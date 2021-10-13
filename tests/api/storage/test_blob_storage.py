from datetime import datetime
from pathlib import Path

from isar.models.mission import Mission
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.storage.storage_service import StorageService
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.inspection.formats import Image
from robot_interface.models.inspection.inspection import (
    Inspection,
    InspectionResult,
    TimeIndexedPose,
)
from robot_interface.models.inspection.metadata import ImageMetadata
from robot_interface.models.inspection.references import ImageReference
from tests.mocks.blob_storage import BlobStorageMock

MISSION_ID = "some-mission-id"
INSPECTION_ID = "some-inspection-id"
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


def test_blob_storage_store():
    blob_storage: BlobStorageMock = BlobStorageMock()
    storage_service: StorageService = StorageService(storage=blob_storage)
    data_bytes: bytes = b"Lets say this is some image data"
    inspection_result: InspectionResult = Image(
        id=INSPECTION_ID, metadata=ARBITRARY_IMAGE_METADATA, data=data_bytes
    )

    storage_service.store(mission_id=MISSION_ID, result=inspection_result)
    expected_path_to_image: Path = Path(
        f"{MISSION_ID}/sensor_data/image/{MISSION_ID}_image_{INSPECTION_ID}.jpg"
    )

    assert blob_storage.blob_exists(
        path_to_blob=expected_path_to_image
    ), "Failed to upload result to SLIMM"


def test_blob_storage_store_metadata():
    blob_storage: BlobStorageMock = BlobStorageMock()
    storage_service: StorageService = StorageService(storage=blob_storage)
    inspection: Inspection = ImageReference(INSPECTION_ID, ARBITRARY_IMAGE_METADATA)
    mission: Mission = Mission(
        mission_steps=[],
        mission_id=MISSION_ID,
        inspections=[inspection],
        mission_metadata=MissionMetadata(MISSION_ID),
    )

    storage_service.store_metadata(mission=mission)

    assert blob_storage.blob_exists(
        path_to_blob=Path(f"{MISSION_ID}/{MISSION_ID}_META.json")
    ), "Failed to upload mission metadata to SLIMM"
    assert blob_storage.blob_exists(
        path_to_blob=Path(
            f"{MISSION_ID}/sensor_data/image/{MISSION_ID}_image_NAVI.json"
        )
    ), "Failed to upload image metadata to SLIMM"
