import logging
import queue
from collections import deque
from copy import deepcopy
from typing import Deque, Optional, Tuple

from injector import Injector, inject
from transitions import Machine

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
from isar.state_machine.states import Cancel, Collect, Idle, Monitor, Off, Send
from isar.state_machine.states_enum import States
from isar.storage.storage_service import StorageService
from robot_interface.robot_interface import RobotInterface


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    @inject
    def __init__(
        self,
        queues: Queues,
        robot: RobotInterface,
        storage_service: StorageService,
        transform: Transformation,
        mission_path: str = config.get("mission", "eqrobot_default_mission"),
        sleep_time: float = config.getfloat("mission", "eqrobot_state_machine_sleep"),
        transitions_log_length: int = config.getint(
            "logging", "state_transitions_log_length"
        ),
    ):
        """Initializes the state machine.

        Parameters
        ----------
        queues : Queues
            Queues used for API communication.
        robot : RobotInterface
            Instance of robot interface.
        slimm_service : SlimmService
            Instance of SLIMM service.
        mission_path : str
            Relative path to mission definition.
        sleep_time : float
            Time to sleep inbetween state machine iterations.
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
            Collect(self, transform),
            Cancel(self, storage_service),
        ]
        self.machine = Machine(self, states=self.states, initial="off", queued=True)

        self.sleep_time = sleep_time
        self.mission_path = mission_path
        self.status: Status = Status(
            mission_status=None,
            mission_in_progress=False,
            current_mission_instance_id=None,
            current_mission_step=None,
            mission_schedule=Mission(mission_steps=[]),
            current_state=States(self.state),  # type: ignore
        )
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
        elif next_state == States.Collect:
            self.to_collect()
        else:
            self.logger.error("Not valid state direction.")

    def update_status(self):
        """Updates the current state of the state machine."""
        self.status.current_state = States(self.state)

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
        self.status.mission_status = None
        self.status.mission_in_progress = False
        self.status.current_mission_instance_id = None
        self.status.current_mission_step = None
        self.status.mission_schedule = Mission(mission_steps=[])

        return States.Idle

    def send_status(self):
        """Communicates state machine status."""
        self.queues.mission_status.output.put(deepcopy(self.status))
        self.logger.info(self.status)

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

        if not self.status.mission_in_progress and mission is not None:
            return True, mission
        elif self.status.mission_in_progress:
            self.queues.start_mission.output.put(
                deepcopy(StartMissionMessages.mission_in_progress())
            )
            self.logger.info(StartMissionMessages.mission_in_progress())
            return False, None

        return False, None

    def start_mission(self, mission: Mission):
        """Starts a scheduled mission."""
        self.status.mission_in_progress = True
        self.status.mission_schedule = mission
        self.queues.start_mission.output.put(deepcopy(StartMissionMessages.success()))
        self.logger.info(StartMissionMessages.success())

    def should_stop(self) -> bool:
        """Determines if state machine should be stopped.

        Returns
        -------
        bool
            True if stop signal sent and mission in progress, false otherwise.

        """
        try:
            stop: bool = self.queues.stop_mission.input.get(block=False)
        except queue.Empty:
            return False

        if stop and self.status.mission_in_progress:
            return True
        elif stop and not self.status.mission_in_progress:
            message: StopMessage = StopMissionMessages.no_active_missions()
            self.queues.stop_mission.output.put(deepcopy(message))
            self.logger.info(message)
            return False

        return False

    def stop_mission(self):
        """Stops a mission in progress."""
        self.status.mission_in_progress = False
        message: StopMessage = StopMissionMessages.success()
        self.queues.stop_mission.output.put(deepcopy(message))
        self.logger.info(message)

    def _log_state_transition(self, next_state):
        """Logs all state transitions that are not self-transitions."""
        if next_state != self.status.current_state:
            self.transitions_list.append(next_state)


def main(injector: Injector):
    """Starts a state machine instance."""
    state_machine = injector.get(StateMachine)
    state_machine.begin()
