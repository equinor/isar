from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorReason(str, Enum):
    RobotCommunicationException = "robot_communication_exception"
    RobotCommunicationTimeoutException = "robot_communication_timeout_exception"
    RobotInfeasibleTaskException = "robot_infeasible_task_exception"
    RobotInfeasibleMissionException = "robot_infeasible_mission_exception"
    RobotMissionStatusException = "robot_mission_status_exception"
    RobotTaskStatusException = "robot_task_status_exception"
    RobotAPIException = "robot_api_exception"
    RobotActionException = "robot_action_exception"
    RobotInitializeException = "robot_initialize_exception"
    RobotRetrieveDataException = "robot_retrieve_data_exception"
    RobotRetrieveInspectionException = "robot_retrieve_inspection_exception"
    RobotStillStartingMissionException = "robot_still_starting_mission_exception"
    RobotTelemetryException = "robot_telemetry_exception"
    RobotTelemetryNoUpdateException = "robot_telemetry_no_update_exception"
    RobotTelemetryPoseException = "robot_telemetry_pose_exception"
    RobotMapException = "robot_map_exception"
    RobotTransformException = "robot_transform_exception"
    RobotUnknownErrorException = "robot_unknown_error_exception"
    RobotDisconnectedException = "robot_disconnected_exception"


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
# communicate with the robot API. ISAR will retry the request.
class RobotCommunicationException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotCommunicationException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if the communication has timed
# out and ISAR should retry the request.
class RobotCommunicationTimeoutException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotCommunicationTimeoutException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to start the
# current task.
class RobotInfeasibleTaskException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotInfeasibleTaskException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to start the
# current mission.
class RobotInfeasibleMissionException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotInfeasibleMissionException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the status of the current mission.
class RobotMissionStatusException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotMissionStatusException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the status of the current task.
class RobotTaskStatusException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotTaskStatusException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is able to communicate
# with the robot API but the result of the communication leads to an exception. An
# example could be a KeyError while reading from the response dictionary.
class RobotAPIException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotAPIException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to perform a
# requested action. For example the package is unable to stop the robot.
class RobotActionException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotActionException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if something is wrong during
# the initialization of the robot. This exception will cause the mission to fail as
# initialization is performed prior to starting the mission.
class RobotInitializeException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotInitializeException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# data from the API like currently executing missions, status of the current mission
# and similar.
class RobotRetrieveDataException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotRetrieveDataException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to collect
# the inspections that were generated for the currently executing task or mission.
class RobotRetrieveInspectionException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotRetrieveInspectionException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is still starting the
# mission when another action is requested. An example of this can be trying to stop
# the robot while it is still starting the mission.
class RobotStillStartingMissionException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotStillStartingMissionException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# telemetry data. It should be used exclusively by the telemetry publishers and their
# functions.
class RobotTelemetryException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotTelemetryException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to retrieve
# telemetry pose data. It should be used exclusively by the telemetry pose publisher.
class RobotTelemetryPoseException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotTelemetryPoseException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if there is no new telemetry update.
class RobotTelemetryNoUpdateException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotTelemetryNoUpdateException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to load the
# configuration for maps and transformations. This could be caused by faulty
# configuration and this exception will cause ISAR to crash as further execution is not
# advised.
class RobotMapException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotMapException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if it is unable to transform
# the coordinates correctly between asset and robot frame.
class RobotTransformException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotTransformException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if something occurred that
# was unexpected and the error reason is unknown.
class RobotUnknownErrorException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description=error_description,
        )

    pass


# An exception which should be thrown by the robot package if the robot is not connected to the cloud
class RobotDisconnectedException(RobotException):
    def __init__(self, error_description: str) -> None:
        super().__init__(
            error_reason=ErrorReason.RobotDisconnectedException,
            error_description=error_description,
        )

    pass
