from dataclasses import dataclass


@dataclass
class ErrorDescription:
    full_text: str
    short_text: str


class RobotException(Exception):
    def __init__(self, error_description: ErrorDescription = None):
        self.error_description: ErrorDescription = error_description


class RobotCommunicationException(RobotException):
    pass


class RobotInfeasibleStepException(RobotException):
    pass


class RobotInfeasibleMissionException(RobotException):
    pass


class RobotInvalidResponseException(RobotException):
    pass


class RobotMapException(RobotException):
    pass


class RobotInvalidTelemetryException(RobotException):
    pass
