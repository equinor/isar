import json
import logging
from collections import deque
from typing import Any, Deque, Optional

from injector import Injector, inject
from paho.mqtt.client import Client, MQTTMessage
from transitions import Machine

from isar.config import config
from isar.models.communication.messages import (
    StartMessage,
    StartMissionMessages,
    StopMessage,
    StopMissionMessages,
)
from isar.models.mission import Mission
from isar.services.coordinates.transformation import Transformation
from isar.services.readers.base_reader import BaseReader, BaseReaderError
from isar.services.service_connections.mqtt.mqtt_service_interface import (
    MQTTServiceInterface,
)
from isar.state_machine.states import Cancel, Collect, Idle, Monitor, Off, Send
from isar.state_machine.states_enum import States
from isar.storage.storage_service import StorageService
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.step import Step
from robot_interface.robot_interface import RobotInterface


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    @inject
    def __init__(
        self,
        robot: RobotInterface,
        storage_service: StorageService,
        transform: Transformation,
        mqtt_service: MQTTServiceInterface,
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

        self.sleep_time: float = sleep_time
        self.mission_path: str = mission_path

        self.mission_status: Optional[MissionStatus] = None
        self.mission_in_progress: bool = False
        self.current_mission_instance_id: Optional[int] = None
        self.current_mission_step: Step = None
        self.mission_schedule: Mission = Mission(mission_steps=[])
        self.current_state: States = States.Off

        self.predefined_mission_id: Optional[int] = None

        self.transitions_log_length: int = transitions_log_length
        self.transitions_list: Deque[States] = deque([], self.transitions_log_length)

        self.mqtt_service: MQTTServiceInterface = mqtt_service
        self.mqtt_service.subscribe_start_mission(
            callback=self.on_start_mission_callback
        )
        self.start_flag: bool = False

        self.mqtt_service.subscribe_stop_mission(callback=self.on_stop_mission_callback)
        self.stop_flag: bool = False

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

    def update_state(self, state: States) -> None:
        """Updates the current state of the state machine."""
        self.current_state = state

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
        self.mission_status = None
        self.mission_in_progress = False
        self.current_mission_instance_id = None
        self.current_mission_step = None
        self.mission_schedule = Mission(mission_steps=[])
        self.start_flag = False
        self.stop_flag = False
        return States.Idle

    def send_status(self) -> None:
        """Communicates state machine status."""
        self.mqtt_service.publish_mission_status_message(self.mission_status)
        self.mqtt_service.publish_mission_in_progress_message(self.mission_in_progress)
        self.mqtt_service.publish_current_mission_instance_id(
            self.current_mission_instance_id
        )
        self.mqtt_service.publish_current_mission_step(self.current_mission_step)
        self.mqtt_service.publish_mission_schedule(self.mission_schedule)
        self.mqtt_service.publish_current_state(self.current_state)

    def should_start_mission(self) -> StartMessage:
        """Determines if mission should be started.

        Returns
        -------
        Tuple[bool, Optional[Mission]]
            True if no mission in progress, false otherwise.

        """
        if self.mission_in_progress:
            return StartMissionMessages.mission_in_progress()
        return StartMissionMessages.success()

    def start_mission(self, mission: Mission) -> None:
        """Starts a scheduled mission."""
        self.mission_in_progress = True
        self.mission_schedule = mission
        self.start_flag = True
        self.logger.info(StartMissionMessages.success())

    def should_stop(self) -> bool:
        """Determines if state machine should be stopped.

        Returns
        -------
        bool
            True if stop signal sent and mission in progress, false otherwise.

        """
        if self.stop_flag and self.mission_in_progress:
            return True
        return False

    def stop_mission(self) -> None:
        """Stops a mission in progress."""
        self.mission_in_progress = False
        message: StopMessage = StopMissionMessages.success()
        self.logger.info(message)

    def _log_state_transition(self, next_state):
        """Logs all state transitions that are not self-transitions."""
        if next_state != self.current_state:
            self.transitions_list.append(next_state)

    def on_start_mission_callback(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        self.logger.info(f"Received start mission on: {message.topic}")
        mission_dict: dict = json.loads(message.payload.decode())
        try:
            mission: Mission = BaseReader.dict_to_dataclass(
                dataclass_dict=mission_dict,
                target_dataclass=Mission,
                cast_config=[Frame],
                strict_config=True,
            )
        except BaseReaderError:
            return_message: StartMessage = (
                StartMissionMessages.failed_to_create_mission()
            )
            self.mqtt_service.publish_start_mission_ack(return_message)
            return

        return_message = self.should_start_mission()

        if return_message.started:
            self.start_mission(mission)

        self.mqtt_service.publish_start_mission_ack(return_message)

    def on_stop_mission_callback(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        self.logger.info(f"Received stop mission on: {message.topic}")

        if self.mission_in_progress:
            return_message: StopMessage = StopMissionMessages.success()
            self.stop_flag = True
        else:
            return_message = StopMissionMessages.no_active_missions()

        self.mqtt_service.publish_stop_mission_ack(return_message)


def main(injector: Injector):
    """Starts a state machine instance."""
    state_machine = injector.get(StateMachine)
    state_machine.begin()
