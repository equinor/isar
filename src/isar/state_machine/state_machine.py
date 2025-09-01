import json
import logging
from collections import deque
from datetime import datetime, timezone
from threading import Event
from typing import Deque, List, Optional, Tuple

from transitions import Machine
from transitions.core import State

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.mission_planner.task_selector_interface import (
    TaskSelectorInterface,
    TaskSelectorStop,
)
from isar.models.events import Events, SharedState
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.blocked_protective_stop import BlockedProtectiveStop
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.robot_standing_still import RobotStandingStill
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from isar.state_machine.transitions.mission import get_mission_transitions
from isar.state_machine.transitions.return_home import get_return_home_transitions
from isar.state_machine.transitions.robot_status import get_robot_status_transitions
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotRetrieveInspectionException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import TASKS, InspectionTask, Task
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.telemetry.payloads import (
    InterventionNeededPayload,
    MissionAbortedPayload,
    MissionPayload,
    RobotStatusPayload,
    TaskPayload,
)
from robot_interface.utilities.json_service import EnhancedJSONEncoder


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    def __init__(
        self,
        events: Events,
        shared_state: SharedState,
        robot: RobotInterface,
        mqtt_publisher: MqttClientInterface,
        task_selector: TaskSelectorInterface,
        sleep_time: float = settings.FSM_SLEEP_TIME,
        stop_robot_attempts_limit: int = settings.STOP_ROBOT_ATTEMPTS_LIMIT,
        transitions_log_length: int = settings.STATE_TRANSITIONS_LOG_LENGTH,
    ):
        """Initializes the state machine.

        Parameters
        ----------
        events : Events
            Events used for API and robot service communication.
        robot : RobotInterface
            Instance of robot interface.
        mqtt_publisher : MqttClientInterface
            Instance of MQTT client interface which has a publish function
        sleep_time : float
            Time to sleep in between state machine iterations.
        stop_robot_attempts_limit : int
            Maximum attempts to stop the robot when stop command is received
        transitions_log_length : int
            Length of state transition log list.

        """
        self.logger = logging.getLogger("state_machine")

        self.events: Events = events
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.mqtt_publisher: Optional[MqttClientInterface] = mqtt_publisher
        self.task_selector: TaskSelectorInterface = task_selector

        self.signal_state_machine_to_stop: Event = Event()

        # List of states
        # States running mission
        self.monitor_state: State = Monitor(self)
        self.returning_home_state: State = ReturningHome(self)
        self.stopping_state: State = Stopping(self)
        self.paused_state: State = Paused(self)

        # States Waiting for mission
        self.await_next_mission_state: State = AwaitNextMission(self)
        self.home_state: State = Home(self)
        self.robot_standing_still_state: State = RobotStandingStill(self)
        self.intervention_needed_state: State = InterventionNeeded(self)

        # Status states
        self.offline_state: State = Offline(self)
        self.blocked_protective_stopping_state: State = BlockedProtectiveStop(self)
        self.recharging_state: State = Recharging(self)

        # Error and special status states
        self.unknown_status_state: State = UnknownStatus(self)

        self.states: List[State] = [
            self.monitor_state,
            self.returning_home_state,
            self.stopping_state,
            self.paused_state,
            self.await_next_mission_state,
            self.home_state,
            self.robot_standing_still_state,
            self.offline_state,
            self.blocked_protective_stopping_state,
            self.unknown_status_state,
            self.intervention_needed_state,
            self.recharging_state,
        ]

        self.machine = Machine(
            self, states=self.states, initial="unknown_status", queued=True
        )

        self.transitions: List[dict] = []

        self.transitions.extend(get_mission_transitions(self))
        self.transitions.extend(get_return_home_transitions(self))
        self.transitions.extend(get_robot_status_transitions(self))

        self.machine.add_transitions(self.transitions)

        self.stop_robot_attempts_limit: int = stop_robot_attempts_limit
        self.sleep_time: float = sleep_time

        self.current_mission: Optional[Mission] = None
        self.current_task: Optional[TASKS] = None

        self.mission_ongoing: bool = False

        self.current_state: State = States(self.state)  # type: ignore

        self.awaiting_task_status: bool = False

        self.transitions_log_length: int = transitions_log_length
        self.transitions_list: Deque[States] = deque([], self.transitions_log_length)

    #################################################################################

    def _finalize(self) -> None:
        self.publish_mission_status()
        self.log_mission_overview(mission=self.current_mission)
        state_transitions: str = ", ".join(
            [
                f"\n  {transition}" if (i + 1) % 10 == 0 else f"{transition}"
                for i, transition in enumerate(list(self.transitions_list))
            ]
        )
        self.logger.info("State transitions:\n  %s", state_transitions)
        self.reset_state_machine()

    def begin(self):
        """Starts the state machine. Transitions into unknown status state."""
        self.robot_status_changed()  # type: ignore

    def terminate(self):
        self.logger.info("Stopping state machine")
        self.signal_state_machine_to_stop.set()

    def iterate_current_task(self):
        if self.current_task is None:
            raise ValueError("No current task is set")

        if self.current_task.is_finished():
            try:
                self.current_task = self.task_selector.next_task()
                self.current_task.status = TaskStatus.InProgress
                self.publish_task_status(task=self.current_task)
            except TaskSelectorStop:
                # Indicates that all tasks are finished
                self.current_task = None
            self.send_task_status()

    def battery_level_is_above_mission_start_threshold(self):
        return (
            not self.shared_state.robot_battery_level.check()
            < settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
        )

    def update_state(self):
        """Updates the current state of the state machine."""
        self.current_state = States(self.state)  # type: ignore
        self.shared_state.state.update(self.current_state)
        self._log_state_transition(self.current_state)
        self.logger.info("State: %s", self.current_state)
        self.publish_status()

    def reset_state_machine(self) -> None:
        self.logger.info("Resetting state machine")
        self.current_task = None
        self.send_task_status()
        self.current_mission = None
        self.mission_ongoing = False

    def start_mission(self, mission: Mission):
        """Starts a scheduled mission."""
        self.current_mission = mission

        self.task_selector.initialize(tasks=self.current_mission.tasks)

    def send_task_status(self):
        self.shared_state.state_machine_current_task.update(self.current_task)

    def report_task_status(self, task: Task) -> None:
        if task.status == TaskStatus.Failed:
            self.logger.warning(
                f"Task: {str(task.id)[:8]} was reported as failed by the robot"
            )
        elif task.status == TaskStatus.Successful:
            self.logger.info(
                f"{type(task).__name__} task: {str(task.id)[:8]} completed"
            )
        else:
            self.logger.info(
                f"Task: {str(task.id)[:8]} was reported as task.status by the robot"
            )

    def publish_mission_aborted(self, reason: str, can_be_continued: bool) -> None:
        if not self.mqtt_publisher:
            return

        if self.current_mission is None:
            self.logger.warning(
                "Could not publish mission aborted message. No ongoing mission."
            )
            return

        payload: MissionAbortedPayload = MissionAbortedPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=self.current_mission.id,
            reason=reason,
            can_be_continued=can_be_continued,
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_MISSION_ABORTED,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def publish_mission_status(self) -> None:
        if not self.mqtt_publisher:
            return

        error_message: Optional[ErrorMessage] = None
        if self.current_mission:
            if self.current_mission.error_message:
                error_message = self.current_mission.error_message

        payload: MissionPayload = MissionPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=self.current_mission.id if self.current_mission else None,
            status=self.current_mission.status if self.current_mission else None,
            error_reason=error_message.error_reason if error_message else None,
            error_description=(
                error_message.error_description if error_message else None
            ),
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_MISSION,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def publish_task_status(self, task: TASKS) -> None:
        """Publishes the task status to the MQTT Broker"""
        if not self.mqtt_publisher:
            return

        error_message: Optional[ErrorMessage] = None
        if task:
            if task.error_message:
                error_message = task.error_message

        payload: TaskPayload = TaskPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=self.current_mission.id if self.current_mission else None,
            task_id=task.id if task else None,
            status=task.status if task else None,
            task_type=task.type if task else None,
            error_reason=error_message.error_reason if error_message else None,
            error_description=(
                error_message.error_description if error_message else None
            ),
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_TASK,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def publish_intervention_needed(self, error_message: str) -> None:
        """Publishes the intervention needed message to the MQTT Broker"""
        if not self.mqtt_publisher:
            return

        payload: InterventionNeededPayload = InterventionNeededPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            reason=error_message,
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_INTERVENTION_NEEDED,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def publish_status(self) -> None:
        if not self.mqtt_publisher:
            return

        payload: RobotStatusPayload = RobotStatusPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            status=self._current_status(),
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_STATUS,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def _current_status(self) -> RobotStatus:
        if (
            self.current_state == States.RobotStandingStill
            or self.current_state == States.AwaitNextMission
        ):
            return RobotStatus.Available
        elif self.current_state == States.Home:
            return RobotStatus.Home
        elif self.current_state == States.ReturningHome:
            return RobotStatus.ReturningHome
        elif self.current_state == States.Offline:
            return RobotStatus.Offline
        elif self.current_state == States.BlockedProtectiveStop:
            return RobotStatus.BlockedProtectiveStop
        elif self.current_state == States.InterventionNeeded:
            return RobotStatus.InterventionNeeded
        elif self.current_state == States.Recharging:
            return RobotStatus.Recharging
        else:
            return RobotStatus.Busy

    def _log_state_transition(self, next_state) -> None:
        """Logs all state transitions that are not self-transitions."""
        self.transitions_list.append(next_state)

    def log_mission_overview(self, mission: Mission) -> None:
        """Log an overview of the tasks in a mission"""
        log_statements: List[str] = []
        for task in mission.tasks:
            log_statements.append(
                f"{type(task).__name__:<20} {str(task.id)[:8]:<32} -- {task.status}"
            )
        log_statement: str = "\n".join(log_statements)

        self.logger.info("Mission overview:\n%s", log_statement)

    def _make_control_mission_response(self) -> ControlMissionResponse:
        return ControlMissionResponse(
            mission_id=self.current_mission.id if self.current_mission else None,
            mission_status=(
                self.current_mission.status if self.current_mission else None
            ),
            task_id=self.current_task.id if self.current_task else None,
            task_status=self.current_task.status if self.current_task else None,
        )

    def _queue_empty_response(self) -> None:
        self.events.api_requests.stop_mission.response.put(
            ControlMissionResponse(
                mission_id="None",
                mission_status="None",
                task_id="None",
                task_status="None",
            )
        )

    def should_upload_inspections(self) -> bool:
        if settings.UPLOAD_INSPECTIONS_ASYNC:
            return False

        return (
            self.current_task.is_finished()
            and self.current_task.status == TaskStatus.Successful
            and isinstance(self.current_task, InspectionTask)
        )

    def queue_inspections_for_upload(
        self, mission: Mission, current_task: InspectionTask, logger: logging.Logger
    ) -> None:
        try:
            inspection: Inspection = self.robot.get_inspection(task=current_task)
            if current_task.inspection_id != inspection.id:
                logger.warning(
                    f"The inspection_id of task ({current_task.inspection_id}) "
                    f"and result ({inspection.id}) is not matching. "
                    f"This may lead to confusions when accessing the inspection later"
                )

        except (RobotRetrieveInspectionException, RobotException) as e:
            error_message: ErrorMessage = ErrorMessage(
                error_reason=e.error_reason, error_description=e.error_description
            )
            self.current_task.error_message = error_message
            logger.error(
                f"Failed to retrieve inspections because: {e.error_description}"
            )
            return

        except Exception as e:
            logger.error(
                f"Failed to retrieve inspections because of unexpected error: {e}"
            )
            return

        if not inspection:
            logger.warning(
                f"No inspection result data retrieved for task {str(current_task.id)[:8]}"
            )

        inspection.metadata.tag_id = current_task.tag_id

        message: Tuple[Inspection, Mission] = (
            inspection,
            mission,
        )
        self.events.upload_queue.put(message)
        logger.info(f"Inspection result: {str(inspection.id)[:8]} queued for upload")


def main(state_machine: StateMachine):
    """Starts a state machine instance."""
    state_machine.begin()
