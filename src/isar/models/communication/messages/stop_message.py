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
    def queue_timeout() -> StopMessage:
        return StopMessage(
            stopped=False, message="Waiting for return message on queue timed out"
        )

    @staticmethod
    def no_active_missions() -> StopMessage:
        return StopMessage(stopped=False, message="No mission is currently active")
