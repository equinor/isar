class RobotException(Exception):
    pass


class RobotInvalidTaskExpection(RobotException):
    pass


class RobotCommunicationException(RobotException):
    pass


class RobotInvalidResponseException(RobotException):
    pass


class RobotMapException(RobotException):
    pass
