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


class RobotLowBatteryException(RobotException):
    def __init__(self, battery_level):
        self.battery_level = battery_level
