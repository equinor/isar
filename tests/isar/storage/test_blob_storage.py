from datetime import datetime

from alitra import Frame, Orientation, Pose, Position

from robot_interface.models.inspection.inspection import ImageMetadata

MISSION_ID = "some-mission-id"
ARBITRARY_IMAGE_METADATA = ImageMetadata(
    start_time=datetime.now(),
    pose=Pose(
        Position(0, 0, 0, Frame("asset")),
        Orientation(0, 0, 0, 1, Frame("asset")),
        Frame("asset"),
    ),
    file_type="jpg",
)
DATA_BYTES: bytes = b"Lets say this is some image data"
