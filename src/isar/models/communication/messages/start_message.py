from dataclasses import dataclass

from isar.models.communication.message import Message


@dataclass
class StartMessage(Message):
    started: bool


class StartMissionMessages:
    @staticmethod
    def success() -> StartMessage:
        return StartMessage(started=True, message="Mission started")

    @staticmethod
    def mission_not_found() -> StartMessage:
        return StartMessage(started=False, message="Mission was not found")

    @staticmethod
    def mission_in_progress() -> StartMessage:
        return StartMessage(started=False, message="A mission is already in progress")

    @staticmethod
    def queue_timeout() -> StartMessage:
        return StartMessage(
            started=False, message="Waiting for return message on queue timed out"
        )
