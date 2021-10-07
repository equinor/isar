from dataclasses import dataclass

from isar.models.communication.message import Message


@dataclass
class StopMessage(Message):
    stopped: bool


class StopMissionMessages:
    @staticmethod
    def success() -> StopMessage:
        return StopMessage(stopped=True, message="Mission stopping")

    @staticmethod
    def ack_timeout() -> StopMessage:
        return StopMessage(stopped=False, message="Acknowledgement timed out")

    @staticmethod
    def no_active_missions() -> StopMessage:
        return StopMessage(stopped=False, message="No mission is currently active")
