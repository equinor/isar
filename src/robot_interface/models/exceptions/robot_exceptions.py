class RobotException(Exception):
    pass


class RobotCommunicationException(RobotException):
    pass


class RobotInvalidResponseException(RobotException):
    pass
