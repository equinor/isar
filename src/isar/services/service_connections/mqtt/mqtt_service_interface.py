from abc import ABCMeta, abstractmethod
from typing import Optional

from isar.models.communication.messages import StartMessage, StopMessage
from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.step import Step


class MQTTServiceInterface(metaclass=ABCMeta):
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def time_since_disconnect(self) -> float:
        pass

    @abstractmethod
    def publish_mission_status_message(self, status: MissionStatus) -> None:
        pass

    @abstractmethod
    def publish_mission_in_progress_message(self, mission_in_progress: bool) -> None:
        pass

    @abstractmethod
    def publish_current_mission_instance_id(
        self, mission_instance_id: Optional[int]
    ) -> None:
        pass

    @abstractmethod
    def publish_current_mission_step(self, mission_step: Optional[Step]) -> None:
        pass

    @abstractmethod
    def publish_mission_schedule(self, mission_schedule: Mission) -> None:
        pass

    @abstractmethod
    def publish_current_state(self, state: States) -> None:
        pass

    @abstractmethod
    def publish_start_mission(self, mission: Mission) -> None:
        pass

    @abstractmethod
    def publish_start_mission_ack(self, start_mission_message: StartMessage) -> None:
        pass

    @abstractmethod
    def publish_stop_mission(self) -> None:
        pass

    @abstractmethod
    def publish_stop_mission_ack(self, stop_mission_message: StopMessage) -> None:
        pass

    @abstractmethod
    def subscribe_start_mission(self, callback=None) -> None:
        pass

    @abstractmethod
    def subscribe_start_mission_ack(self, callback=None) -> None:
        pass

    @abstractmethod
    def subscribe_stop_mission(self, callback=None) -> None:
        pass

    @abstractmethod
    def subscribe_stop_mission_ack(self, callback=None) -> None:
        pass


class MQTTConnectionError(Exception):
    pass
