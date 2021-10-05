import abc
from abc import abstractmethod

from models.geometry.pose import Pose


class RobotTelemetryInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "get_robot_pose")
            and callable(subclass.get_robot_pose)
            or NotImplemented
        )

    @abstractmethod
    def robot_pose(self) -> Pose:
        """
        Retrieve the current pose of the robot as x, y, z coordinates and quaternion.
        :return: Representation of the robots pose.
        """
        raise NotImplementedError
