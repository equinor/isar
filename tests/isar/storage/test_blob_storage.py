from datetime import datetime

from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.inspection.inspection import (
    ImageMetadata,
    TimeIndexedPose,
)

MISSION_ID = "some-mission-id"
ARBITRARY_IMAGE_METADATA = ImageMetadata(
    datetime.now(),
    TimeIndexedPose(
        Pose(
            Position(0, 0, 0, Frame.Asset),
            Orientation(0, 0, 0, 1, Frame.Asset),
            Frame.Asset,
        ),
        datetime.now(),
    ),
    file_type="jpg",
)
DATA_BYTES: bytes = b"Lets say this is some image data"
