from datetime import datetime
from pathlib import Path

from isar.models.mission import Mission
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.storage.storage_service import StorageService
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.inspection.inspection import (
    Image,
    ImageMetadata,
    Inspection,
    TimeIndexedPose,
)
from tests.mocks.blob_storage import StorageMock

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


def test_blob_storage_store():
    blob_storage: StorageMock = StorageMock()
    storage_service: StorageService = StorageService(storage=blob_storage)
    inspection: Inspection = Image(metadata=ARBITRARY_IMAGE_METADATA)
    inspection.data = DATA_BYTES

    storage_service.store(mission_id=MISSION_ID, result=inspection)
    expected_path_to_image: Path = Path(
        f"{MISSION_ID}/sensor_data/image/{MISSION_ID}_image_{inspection.id}.jpg"
    )

    assert blob_storage.blob_exists(
        path=expected_path_to_image
    ), "Failed to upload result to SLIMM"


def test_blob_storage_store_metadata():
    blob_storage: StorageMock = StorageMock()
    storage_service: StorageService = StorageService(storage=blob_storage)
    inspection: Inspection = Image(ARBITRARY_IMAGE_METADATA)
    inspection.data = DATA_BYTES

    mission: Mission = Mission(
        tasks=[], id=MISSION_ID, metadata=MissionMetadata(MISSION_ID)
    )

    storage_service.store_metadata(mission=mission, inspections=[inspection])

    assert blob_storage.blob_exists(
        path=Path(f"{MISSION_ID}/{MISSION_ID}_META.json")
    ), "Failed to upload mission metadata to SLIMM"
    assert blob_storage.blob_exists(
        path=Path(f"{MISSION_ID}/sensor_data/image/{MISSION_ID}_image_NAVI.json")
    ), "Failed to upload image metadata to SLIMM"
