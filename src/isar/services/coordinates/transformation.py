import logging
from typing import Optional

from alitra import AlignFrames, FrameTransform, Point, Quaternion

from isar.models.map.map_config import MapConfig
from isar.services.coordinates.coordinate_utilities import (
    orientation_from_quaternion,
    quaternion_from_orientation,
)
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position


class Transformation:
    def __init__(self, map_config: MapConfig):
        self.logger = logging.getLogger("state_machine")
        self.transform: FrameTransform = AlignFrames.align_frames(
            map_config.robot_reference_points, map_config.asset_reference_points, "z"
        )

    def transform_position(self, position: Position, to_: Frame) -> Optional[Position]:
        """
        Transforms a Position object to a Position object in the to_ frame.
        :param position: A Position object.
        :param to_: Coordinate frame to transfer to given as a Frame object.
        :return: A Position object with to_ as the frame.
        """
        points_from: Point = Point(
            x=position.x, y=position.y, z=position.z, frame=position.frame.value
        )
        point_to: Point = self.transform.transform_point(
            points_from, from_=position.frame.value, to_=to_.value
        )

        position_to: Position = Position(
            x=point_to.x, y=point_to.y, z=point_to.z, frame=to_
        )

        return position_to

    def transform_orientation(
        self, orientation: Orientation, to_: Frame
    ) -> Optional[Orientation]:
        """
        Transforms an Orientation object to an Orientation object in the to_ frame.
        :param orientation: An Orientation object.
        :param to_: Coordinate frame to transfer to given as a Frame object.
        :return: An Orientation object with to_ as the frame.
        """
        quaternion_from: Quaternion = quaternion_from_orientation(
            orientation=orientation
        )

        quaternion_to: Quaternion = self.transform.transform_quaternion(
            quaternion_from, from_=orientation.frame.value, to_=to_.value
        )

        orientation_to: Orientation = orientation_from_quaternion(
            quaternion=quaternion_to
        )
        return orientation_to

    def transform_pose(self, pose: Pose, to_: Frame) -> Optional[Pose]:
        """
        Transforms a Pose object to a Pose object in the to_ frame.
        :param pose: A Pose object.
        :param to_: Coordinate frame to transfer to given as a Frame object.
        :return: A Pose object with to_ as the frame.
        """
        position_to: Position = self.transform_position(position=pose.position, to_=to_)
        orientation_to: Orientation = self.transform_orientation(
            orientation=pose.orientation, to_=to_
        )

        pose_to: Pose = Pose(
            position=position_to, orientation=orientation_to, frame=to_
        )

        return pose_to
