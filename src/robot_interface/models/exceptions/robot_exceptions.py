class RobotException(Exception):
    pass


class RobotCommunicationException(RobotException):
    pass


class RobotInfeasibleTaskException(RobotException):
    pass


class RobotInvalidResponseException(RobotException):
    pass


class RobotMapException(RobotException):
    pass
