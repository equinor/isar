class RobotException(Exception):
    pass


class RobotCommunicationException(RobotException):
    pass


class RobotInfeasibleStepException(RobotException):
    pass


class RobotInvalidResponseException(RobotException):
    pass


class RobotMapException(RobotException):
    pass


class RobotInvalidTelemetryException(RobotException):
    pass
