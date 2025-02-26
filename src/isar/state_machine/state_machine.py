import json
import logging
import queue
from collections import deque
from datetime import datetime, timezone
from typing import Deque, List, Optional

from injector import inject
from transitions import Machine
from transitions.core import State

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.mission_planner.task_selector_interface import (
    TaskSelectorInterface,
    TaskSelectorStop,
)
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.events import Events, SharedState
from isar.state_machine.states.blocked_protective_stop import BlockedProtectiveStop
from isar.state_machine.states.idle import Idle
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.off import Off
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.stop import Stop
from isar.state_machine.states_enum import States
from isar.state_machine.transitions.fail_mission import (
    report_failed_mission_and_finalize,
)
from isar.state_machine.transitions.finish_mission import finish_mission
from isar.state_machine.transitions.pause import pause_mission
from isar.state_machine.transitions.resume import resume_mission
from isar.state_machine.transitions.start_mission import (
    initialize_robot,
    initiate_mission,
    put_start_mission_on_queue,
    set_mission_to_in_progress,
    trigger_start_mission_or_task_event,
)
from isar.state_machine.transitions.stop import stop_mission
from isar.state_machine.transitions.utils import def_transition
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import TASKS
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.telemetry.payloads import (
    MissionPayload,
    RobotStatusPayload,
    TaskPayload,
)
from robot_interface.utilities.json_service import EnhancedJSONEncoder


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    @inject
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

        # List of states
        self.stop_state: State = Stop(self)
        self.paused_state: State = Paused(self)
        self.idle_state: State = Idle(self)
        self.monitor_state: State = Monitor(self)
        self.off_state: State = Off(self)
        self.offline_state: State = Offline(self)
        self.blocked_protective_stop: State = BlockedProtectiveStop(self)

        self.states: List[State] = [
            self.off_state,
            self.idle_state,
            self.monitor_state,
            self.stop_state,
            self.paused_state,
            self.offline_state,
            self.blocked_protective_stop,
        ]

        self.machine = Machine(self, states=self.states, initial="off", queued=True)
        self.machine.add_transitions(
            [
                {
                    "trigger": "start_machine",
                    "source": self.off_state,
                    "dest": self.idle_state,
                },
                {
                    "trigger": "pause",
                    "source": self.monitor_state,
                    "dest": self.paused_state,
                    "before": def_transition(self, pause_mission),
                },
                {
                    "trigger": "stop",
                    "source": [
                        self.idle_state,
                        self.monitor_state,
                        self.paused_state,
                    ],
                    "dest": self.stop_state,
                },
                {
                    "trigger": "request_mission_start",
                    "source": self.idle_state,
                    "dest": self.monitor_state,
                    "prepare": def_transition(self, put_start_mission_on_queue),
                    "conditions": [
                        def_transition(self, initiate_mission),
                        def_transition(self, initialize_robot),
                    ],
                    "before": [
                        def_transition(self, set_mission_to_in_progress),
                        def_transition(self, trigger_start_mission_or_task_event),
                    ],
                },
                {
                    "trigger": "request_mission_start",
                    "source": self.idle_state,
                    "dest": self.idle_state,
                },
                {
                    "trigger": "mission_failed_to_start",
                    "source": self.monitor_state,
                    "dest": self.idle_state,
                    "before": def_transition(self, report_failed_mission_and_finalize),
                },
                {
                    "trigger": "resume",
                    "source": self.paused_state,
                    "dest": self.monitor_state,
                    "before": def_transition(self, resume_mission),
                },
                {
                    "trigger": "mission_finished",
                    "source": self.monitor_state,
                    "dest": self.idle_state,
                    "before": def_transition(self, finish_mission),
                },
                {
                    "trigger": "mission_stopped",
                    "source": self.stop_state,
                    "dest": self.idle_state,
                    "before": def_transition(self, stop_mission),
                },
                {
                    "trigger": "robot_turned_offline",
                    "source": [self.idle_state, self.blocked_protective_stop],
                    "dest": self.offline_state,
                },
                {
                    "trigger": "robot_turned_online",
                    "source": self.offline_state,
                    "dest": self.idle_state,
                },
                {
                    "trigger": "robot_protective_stop_engaged",
                    "source": [self.idle_state, self.offline_state],
                    "dest": self.blocked_protective_stop,
                },
                {
                    "trigger": "robot_protective_stop_disengaged",
                    "source": self.blocked_protective_stop,
                    "dest": self.idle_state,
                },
            ]
        )

        self.stop_robot_attempts_limit: int = stop_robot_attempts_limit
        self.sleep_time: float = sleep_time

        self.current_mission: Optional[Mission] = None
        self.current_task: Optional[TASKS] = None

        self.mission_ongoing: bool = False

        self.current_state: State = States(self.state)  # type: ignore

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
        self.logger.info(f"State transitions:\n  {state_transitions}")
        self.reset_state_machine()

    def begin(self):
        """Starts the state machine. Transitions into idle state."""
        self.to_idle()  # type: ignore

    def iterate_current_task(self):
        if self.current_task.is_finished():
            try:
                self.current_task = self.task_selector.next_task()
                self.current_task.status = TaskStatus.InProgress
                self.publish_task_status(task=self.current_task)
            except TaskSelectorStop:
                # Indicates that all tasks are finished
                self.current_task = None
            self.send_task_status()

    def update_state(self):
        """Updates the current state of the state machine."""
        self.current_state = States(self.state)  # type: ignore
        self.send_state_status()
        self._log_state_transition(self.current_state)
        self.logger.info(f"State: {self.current_state}")
        self.publish_status()

    def reset_state_machine(self) -> None:
        self.logger.info("Resetting state machine")
        self.current_task = None
        self.send_task_status()
        self.current_mission = None

    def start_mission(self, mission: Mission):
        """Starts a scheduled mission."""
        self.current_mission = mission

        self.task_selector.initialize(tasks=self.current_mission.tasks)

    def should_start_mission(self) -> Optional[StartMissionMessage]:
        try:
            return self.events.api_requests.api_start_mission.input.get(block=False)
        except queue.Empty:
            return None

    def should_stop_mission(self) -> bool:
        try:
            return self.events.api_requests.api_stop_mission.input.get(block=False)
        except queue.Empty:
            return False

    def should_pause_mission(self) -> bool:
        try:
            return self.events.api_requests.api_pause_mission.input.get(block=False)
        except queue.Empty:
            return False

    def get_task_status_event(self) -> Optional[TaskStatus]:
        try:
            return self.events.robot_service_events.robot_task_status.get(block=False)
        except queue.Empty:
            return None

    def request_task_status(self, task_id: str) -> None:
        self.events.state_machine_events.state_machine_task_status_request.put(task_id)

    def get_mission_started_event(self) -> bool:
        try:
            return self.events.robot_service_events.robot_mission_started.get(
                block=False
            )
        except queue.Empty:
            return False

    def get_mission_failed_event(self) -> Optional[ErrorMessage]:
        try:
            return self.events.robot_service_events.robot_mission_failed.get(
                block=False
            )
        except queue.Empty:
            return None

    def get_task_failure_event(self) -> Optional[ErrorMessage]:
        try:
            return self.events.robot_service_events.robot_task_status_failed.get(
                block=False
            )
        except queue.Empty:
            return None

    def should_resume_mission(self) -> bool:
        try:
            return self.events.api_requests.api_resume_mission.input.get(block=False)
        except queue.Empty:
            return False

    def get_robot_status(self) -> bool:
        try:
            return self.shared_state.robot_status.check()
        except queue.Empty:
            return False

    def send_state_status(self) -> None:
        self.shared_state.state.update(self.current_state)

    def send_task_status(self):
        self.shared_state.state_machine_current_task.update(self.current_task)

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
        if self.current_state == States.Idle:
            return RobotStatus.Available
        elif self.current_state == States.Offline:
            return RobotStatus.Offline
        elif self.current_state == States.BlockedProtectiveStop:
            return RobotStatus.BlockedProtectiveStop
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

        self.logger.info(f"Mission overview:\n{log_statement}")

    def _make_control_mission_response(self) -> ControlMissionResponse:
        return ControlMissionResponse(
            mission_id=self.current_mission.id,
            mission_status=self.current_mission.status,
            task_id=self.current_task.id,
            task_status=self.current_task.status,
        )

    def _queue_empty_response(self) -> None:
        self.events.api_requests.api_stop_mission.output.put(
            ControlMissionResponse(
                mission_id="None",
                mission_status="None",
                task_id="None",
                task_status="None",
            )
        )


def main(state_machine: StateMachine):
    """Starts a state machine instance."""
    state_machine.begin()
