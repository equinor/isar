from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorReason(str, Enum):
    RobotCommunicationException: str = "robot_communication_exception"
    RobotInfeasibleStepException: str = "robot_infeasible_step_exception"
    RobotInfeasibleMissionException: str = "robot_infeasible_mission_exception"
    RobotMissionStatusException: str = "robot_mission_status_exception"
    RobotStepStatusException: str = "robot_step_status_exception"
    RobotAPIException: str = "robot_api_exception"
    RobotActionException: str = "robot_action_exception"
    RobotInitializeException: str = "robot_initialize_exception"
    RobotRetrieveDataException: str = "robot_retrieve_data_exception"
    RobotRetrieveInspectionException: str = "robot_retrieve_inspection_exception"
    RobotTelemetryException: str = "robot_telemetry_exception"
    RobotMapException: str = "robot_map_exception"
    RobotTransformException: str = "robot_transform_exception"
    RobotUnknownErrorException: str = "robot_unknown_error_exception"


@dataclass
class ErrorMessage:
    error_reason: Optional[ErrorReason]
    error_description: str


# This is the base exception class for exceptions that should be raised from the robot
# package and handled in ISAR. Please peruse the different subclasses for information
# on which exceptions to use where.
class RobotException(Exception):
    def __init__(self, error_reason: ErrorReason, error_description: str):
        self.error_reason: ErrorReason = error_reason
        self.error_description: str = error_description


# An exception which should be thrown by the robot package if it is unable to
# communicate with the robot API.
class RobotCommunicationException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to start the
# current step.
class RobotInfeasibleStepException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to start the
# current mission.
class RobotInfeasibleMissionException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the status of the current mission.
class RobotMissionStatusException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the status of the current step.
class RobotStepStatusException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is able to communicate
# with the robot API but the result of the communication leads to an exception. An
# example could be a KeyError while reading from the response dictionary.
class RobotAPIException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to perform a
# requested action. For example the package is unable to stop the robot.
class RobotActionException(RobotException):
    pass


# An exception which should be thrown by the robot package if something is wrong during
# the initialization of the robot. This exception will cause the mission to fail as
# initialization is performed prior to starting the mission.
class RobotInitializeException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# data from the API like currently executing missions, status of the current mission
# and similar.
class RobotRetrieveDataException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the inspections that were generated for the currently executing step or mission.
class RobotRetrieveInspectionException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# telemetry data. It should be used exclusively by the telemetry publishers and their
# functions.
class RobotTelemetryException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to load the
# configuration for maps and transformations. This could be caused by faulty
# configuration and this exception will cause ISAR to crash as further execution is not
# advised.
class RobotMapException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to transform
# the coordinates correctly between asset and robot frame.
class RobotTransformException(RobotException):
    pass


# An exception which should be thrown by the robot package if something occurred that
# was unexpected and the error reason is unknown.
class RobotUnknownErrorException(RobotException):
    pass
