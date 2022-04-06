import json
import logging
import queue
from collections import deque
from copy import deepcopy
from typing import Deque, Optional, Tuple

from injector import Injector, inject
from transitions import Machine
from transitions.core import State

from isar.config.settings import settings
from isar.models.communication.messages import (
    StartMissionMessages,
    StopMessage,
    StopMissionMessages,
)
from isar.models.communication.queues.queues import Queues
from isar.models.communication.status import Status
from isar.models.mission import Mission
from isar.services.service_connections.mqtt.mqtt_client import MqttClientInterface
from isar.services.utilities.json_service import EnhancedJSONEncoder
from isar.state_machine.states import Finalize, Idle, InitiateTask, Monitor, Off
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions import RobotException
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import Task
from robot_interface.robot_interface import RobotInterface


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    @inject
    def __init__(
        self,
        queues: Queues,
        robot: RobotInterface,
        mqtt_client: MqttClientInterface,
        sleep_time: float = settings.FSM_SLEEP_TIME,
        stop_robot_attempts_limit: int = settings.STOP_ROBOT_ATTEMPTS_LIMIT,
        transitions_log_length: int = settings.STATE_TRANSITIONS_LOG_LENGTH,
    ):
        """Initializes the state machine.

        Parameters
        ----------
        queues : Queues
            Queues used for API communication.
        robot : RobotInterface
            Instance of robot interface.
        sleep_time : float
            Time to sleep in between state machine iterations.
        stop_robot_attempts_limit : int
            Maximum attempts to stop the robot when stop command is received
        transitions_log_length : int
            Length of state transition log list.

        """
        self.logger = logging.getLogger("state_machine")

        self.queues = queues
        self.robot = robot
        self.mqtt_client: Optional[MqttClientInterface] = mqtt_client

        self.states = [
            Off(self),
            Idle(self),
            InitiateTask(self),
            Monitor(self),
            Finalize(self),
        ]
        self.machine = Machine(
            self,
            states=self.states,
            initial="off",
            queued=True,
        )
        self.stop_robot_attempts_limit = stop_robot_attempts_limit
        self.sleep_time = sleep_time

        self.mission_in_progress: bool = False
        self.current_mission: Mission = Mission(tasks=[])
        self.current_task: Optional[Task] = None
        self.current_task_index: int = -1

        self.current_state: State = States(self.state)  # type: ignore

        self.predefined_mission_id: Optional[int] = None

        self.transitions_log_length = transitions_log_length
        self.transitions_list: Deque[States] = deque([], self.transitions_log_length)

    def begin(self):
        """Starts the state machine.

        Transitions into idle state.

        """
        self._log_state_transition(States.Idle)
        self.to_idle()

    def to_next_state(self, next_state):
        """Transitions state machine to next state."""
        self._log_state_transition(next_state)

        if next_state == States.Idle:
            self.to_idle()
        elif next_state == States.InitiateTask:
            self.to_initiate_task()
        elif next_state == States.Monitor:
            self.to_monitor()
        elif next_state == States.Finalize:
            self.to_finalize()
        else:
            self.logger.error("Not valid state direction.")

    def update_current_task(self):
        self.current_task_index += 1
        if len(self.current_mission.tasks) > self.current_task_index:
            self.current_task = self.current_mission.tasks[self.current_task_index]
        else:
            self.current_task = None

    def update_state(self):
        """Updates the current state of the state machine."""
        self.current_state = States(self.state)
        self.logger.info(f"State: {self.current_state}")

        payload: str = json.dumps({"state": self.current_state})

        if self.mqtt_client:
            self.mqtt_client.publish(
                topic=settings.ISAR_STATE,
                payload=payload,
                retain=True,
            )

    def reset_state_machine(self) -> States:
        """Resets the state machine.

        The mission status and progress is reset, and mission schedule
        is emptied.

        Transitions to idle state.

        Returns
        -------
        States
            Idle state.

        """

        self.mission_in_progress = False
        self.current_task = None
        self.current_task_index = -1
        self.current_mission = Mission(tasks=[])

        return States.Idle

    def send_status(self):
        """Communicates state machine status."""
        status = Status(
            mission_in_progress=self.mission_in_progress,
            current_task=self.current_task,
            current_mission=self.current_mission,
            current_state=self.current_state,
        )
        self.queues.mission_status.output.put(deepcopy(status))

    def should_send_status(self) -> bool:
        """Determines if mission status should be sent.

        Returns
        -------
        bool
            True if nonempty queue, false otherwise.

        """
        try:
            send: bool = self.queues.mission_status.input.get(block=False)
            return send
        except queue.Empty:
            return False

    def should_start_mission(self) -> Tuple[bool, Optional[Mission]]:
        """Determines if mission should be started.

        Returns
        -------
        Tuple[bool, Optional[Mission]]
            True if no mission in progress, false otherwise.

        """
        try:
            mission: Mission = self.queues.start_mission.input.get(block=False)
        except queue.Empty:
            return False, None

        if not self.mission_in_progress and mission is not None:
            return True, mission
        elif self.mission_in_progress:
            self.queues.start_mission.output.put(
                deepcopy(StartMissionMessages.mission_in_progress())
            )
            self.logger.info(StartMissionMessages.mission_in_progress())
            return False, None

        return False, None

    def start_mission(self, mission: Mission):
        """Starts a scheduled mission."""
        self.mission_in_progress = True
        self.current_mission = mission
        self.queues.start_mission.output.put(deepcopy(StartMissionMessages.success()))
        self.logger.info(f"Starting new mission: {mission.id}")
        self.log_task_overview(mission=mission)

    def should_stop_mission(self) -> bool:
        """Determines if the running mission should be stopped.

        Returns
        -------
        bool
            True if stop signal is sent and mission is in progress, false otherwise.

        """
        try:
            stop: bool = self.queues.stop_mission.input.get(block=False)
        except queue.Empty:
            return False

        if stop and self.mission_in_progress:
            return True
        elif stop and not self.mission_in_progress:
            message: StopMessage = StopMissionMessages.no_active_missions()
            self.queues.stop_mission.output.put(deepcopy(message))
            self.logger.info(message)
            return False

        return False

    def stop_mission(self):
        """Stops a mission in progress."""
        failure: bool = False
        stop_attempts = 0
        while True:
            try:
                self.robot.stop()
                break
            except RobotException:
                stop_attempts += 1
                if stop_attempts < self.stop_robot_attempts_limit:
                    continue
                self.logger.warning(StopMissionMessages.failure())
                failure = True
                break

        message: StopMessage = (
            StopMissionMessages.failure() if failure else StopMissionMessages.success()
        )
        self.queues.stop_mission.output.put(deepcopy(message))
        self.logger.info(message)
        if not failure:
            self.mission_in_progress = False

    def publish_task_status(self) -> None:
        """Publishes the current task status to the MQTT Broker"""
        payload: str = json.dumps(
            {
                "task_id": self.current_task.id if self.current_task else None,
                "task_status": self.current_task.status if self.current_task else None,
            },
            cls=EnhancedJSONEncoder,
        )

        self.mqtt_client.publish(
            topic=settings.ISAR_TASK_STATUS,
            payload=payload,
            retain=True,
        )

    def publish_mission(self) -> None:
        payload: str = json.dumps(
            {"mission": self.current_mission}, cls=EnhancedJSONEncoder
        )

        self.mqtt_client.publish(
            topic=settings.ISAR_MISSION,
            payload=payload,
            retain=True,
        )

    def _log_state_transition(self, next_state):
        """Logs all state transitions that are not self-transitions."""
        if next_state != self.current_state:
            self.transitions_list.append(next_state)

    def log_task_overview(self, mission: Mission):
        """Log an overview of the tasks in a mission"""
        task_status: str = "\n".join(
            [
                f"{i:>3}  {type(task).__name__:<20} {str(task.id)[:8]:<32} -- {task.status}"
                for i, task in enumerate(mission.tasks)
            ]
        )
        self.logger.info(f"Mission task overview:\n{task_status}")

    def _check_dependencies(self):
        """Check dependencies of previous tasks"""
        if self.current_task and self.current_task.depends_on:
            dependency_tasks = [
                task
                for task in self.current_mission.tasks
                if task.id in self.current_task.depends_on
            ]
            if not all(
                [task.status == TaskStatus.Completed for task in dependency_tasks]
            ):
                return False
        return True


def main(injector: Injector):
    """Starts a state machine instance."""
    state_machine = injector.get(StateMachine)
    state_machine.begin()
