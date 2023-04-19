from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorReason(str, Enum):
    RobotCommunicationException: str = "robot_communication_exception"
    RobotInfeasibleStepException: str = "robot_infeasible_step_exception"
    RobotInfeasibleMissionException: str = "robot_infeasible_mission_exception"
    RobotPerformApiActionException: str = "robot_perform_api_action_exception"
    RobotRetrieveStatusException: str = "robot_retrieve_status_exception"
    RobotRetrieveInspectionException: str = "robot_retrieve_inspection_exception"
    RobotInterpretResponseException: str = "robot_interpret_response_exception"
    RobotTelemetryException: str = "robot_telemetry_exception"
    RobotMapConfigurationException: str = "robot_map_configuration_exception"
    RobotMapTransformException: str = "robot_map_transform_exception"
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
# communicate with the robot.
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


# An exception which should be thrown by the robot package if it is unable to perform
# an update or create operation towards the API. An example could be attempting to
# delete something through the API.
class RobotPerformApiActionException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# status related information from the API like currently executing missions, status of
# the current mission and similar.
class RobotRetrieveStatusException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the inspections that were generated for the currently executing step or mission.
class RobotRetrieveInspectionException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to interpret
# information that has been received from the API. For example, this could be the result
# of a KeyError when accessing a response from the API.
class RobotInterpretResponseException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# telemetry data. It should be used exclusively by the telemetry publishers and their
# functions.
class RobotTelemetryException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to load the
# configuration for maps and transformations. This could be caused by faulty
# configuration and will this exception will cause ISAR to crash as further execution is
# not advised.
class RobotMapConfigurationException(RobotException):
    pass


# An exception which should be thrown by the robot package if it is unable to transform
# the coordinates correctly between asset and robot frame.
class RobotMapTransformException(RobotException):
    pass


# An exception which should be thrown by the robot package if something occurred that
# was unexpected and the error reason is unknown.
class RobotUnknownErrorException(RobotException):
    pass
