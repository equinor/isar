import logging
import queue
from collections import deque
from copy import deepcopy
from typing import Deque, Optional, Tuple

from injector import Injector, inject
from transitions import Machine
from transitions.core import State

from isar.config import config
from isar.models.communication.messages import (
    StartMissionMessages,
    StopMessage,
    StopMissionMessages,
)
from isar.models.communication.queues.queues import Queues
from isar.models.communication.status import Status
from isar.models.mission import Mission
from isar.services.coordinates.transformation import Transformation
from isar.state_machine.states import Cancel, Idle, Monitor, Off, Send
from isar.state_machine.states_enum import States
from isar.storage.storage_service import StorageService
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import Task
from robot_interface.robot_interface import RobotInterface
from robot_interface.models.exceptions import RobotException


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    @inject
    def __init__(
        self,
        queues: Queues,
        robot: RobotInterface,
        storage_service: StorageService,
        transform: Transformation,
        sleep_time: float = config.getfloat("DEFAULT", "fsm_sleep_time"),
        stop_robot_attempts_limit: int = config.getint(
            "DEFAULT", "stop_robot_attempts_limit"
        ),
        transitions_log_length: int = config.getint(
            "DEFAULT", "state_transitions_log_length"
        ),
    ):
        """Initializes the state machine.

        Parameters
        ----------
        queues : Queues
            Queues used for API communication.
        robot : RobotInterface
            Instance of robot interface.
        storage_service : StorageService
            Instance of StorageService.
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

        self.states = [
            Off(self),
            Idle(self),
            Send(self),
            Monitor(self),
            Cancel(self, transform, storage_service),
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
        elif next_state == States.Send:
            self.to_send()
        elif next_state == States.Monitor:
            self.to_monitor()
        elif next_state == States.Cancel:
            self.to_cancel()
        else:
            self.logger.error("Not valid state direction.")

    def update_current_task(self):
        self.current_task_index += 1
        if len(self.current_mission.tasks) > (self.current_task_index):
            self.current_task = self.current_mission.tasks[self.current_task_index]
        else:
            self.current_task = None

    def update_status(self):
        """Updates the current state of the state machine."""
        self.current_state = States(self.state)

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
        self.logger.info(status)

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
        self.logger.info(StartMissionMessages.success())

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
        stop_attempts = 0
        while True:
            try:
                self.robot.stop()
                break
            except RobotException:
                stop_attempts += 1
                if stop_attempts < self.stop_robot_attempts_limit:
                    continue
                self.logger.warning("Failed to stop the robot within maximum attempts!")
                break

        self.mission_in_progress = False
        message: StopMessage = StopMissionMessages.success()
        self.queues.stop_mission.output.put(deepcopy(message))
        self.logger.info(message)

    def _log_state_transition(self, next_state):
        """Logs all state transitions that are not self-transitions."""
        if next_state != self.current_state:
            self.transitions_list.append(next_state)

    def _check_dependencies(self):
        """Check dependencies of previous tasks"""
        if self.current_task and self.current_task.depends_on:
            for task_index in self.current_task.depends_on:
                if (
                    self.current_mission.tasks[task_index].status
                    is not TaskStatus.Completed
                ):
                    return False
        return True


def main(injector: Injector):
    """Starts a state machine instance."""
    state_machine = injector.get(StateMachine)
    state_machine.begin()
