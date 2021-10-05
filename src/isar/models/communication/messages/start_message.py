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
    def bad_request() -> StartMessage:
        return StartMessage(
            started=False, message="Format of input parameters is invalid"
        )

    @staticmethod
    def mission_not_found() -> StartMessage:
        return StartMessage(started=False, message="Mission was not found")

    @staticmethod
    def queue_not_empty() -> StartMessage:
        return StartMessage(started=False, message="Mission queue is not empty")

    @staticmethod
    def state_not_idle() -> StartMessage:
        return StartMessage(started=False, message="Mission is not in idle")

    @staticmethod
    def mission_in_progress() -> StartMessage:
        return StartMessage(started=False, message="A mission is already in progress")

    @staticmethod
    def failed_to_create_mission() -> StartMessage:
        return StartMessage(
            started=False, message="Failed to create a Mission from mission"
        )

    @staticmethod
    def queue_timeout() -> StartMessage:
        return StartMessage(
            started=False, message="Waiting for return message on queue timed out"
        )

    @staticmethod
    def could_not_read_mission_id() -> StartMessage:
        return StartMessage(
            started=False, message="Could not read mission_id parameter"
        )

    @staticmethod
    def invalid_mission_id(mission_id: int) -> StartMessage:
        return StartMessage(
            started=False, message=f"No missions with mission_id {mission_id}"
        )
