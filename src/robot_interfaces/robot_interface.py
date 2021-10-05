from abc import ABCMeta

from robot_interfaces.robot_scheduler_interface import RobotSchedulerInterface
from robot_interfaces.robot_storage_interface import RobotStorageInterface
from robot_interfaces.robot_telemetry_interface import RobotTelemetryInterface


class RobotInterface(metaclass=ABCMeta):
    scheduler: RobotSchedulerInterface
    storage: RobotStorageInterface
    telemetry: RobotTelemetryInterface
