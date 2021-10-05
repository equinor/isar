from datetime import datetime
from pathlib import Path

from isar.models.mission import Mission
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.service_connections.slimm.slimm_service import SlimmService
from models.geometry.frame import Frame
from models.geometry.orientation import Orientation
from models.geometry.pose import Pose
from models.geometry.position import Position
from models.inspections.formats.image import Image
from models.inspections.inspection import Inspection
from models.inspections.inspection_result import InspectionResult
from models.inspections.references.image_reference import ImageReference
from models.metadata.inspection_metadata import TimeIndexedPose
from models.metadata.inspections.image_metadata import ImageMetadata
from tests.mocks.blob_service import BlobServiceMock

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


def test_slimm_service_upload():
    blob_service: BlobServiceMock = BlobServiceMock()
    slimm_service: SlimmService = SlimmService(blob_service=blob_service)
    data_bytes: bytes = b"Lets say this is some image data"
    inspection_result: InspectionResult = Image(
        id=INSPECTION_ID, metadata=ARBITRARY_IMAGE_METADATA, data=data_bytes
    )

    slimm_service.upload(mission_id=MISSION_ID, result=inspection_result)
    expected_path_to_image: Path = Path(
        f"{MISSION_ID}/sensor_data/image/{MISSION_ID}_image_{INSPECTION_ID}.jpg"
    )

    assert blob_service.blob_exists(
        path_to_blob=expected_path_to_image
    ), "Failed to upload result to SLIMM"


def test_slimm_service_upload_metadata():
    blob_service: BlobServiceMock = BlobServiceMock()
    slimm_service: SlimmService = SlimmService(blob_service)
    inspection: Inspection = ImageReference(INSPECTION_ID, ARBITRARY_IMAGE_METADATA)
    mission: Mission = Mission(
        mission_steps=[],
        mission_id=MISSION_ID,
        inspections=[inspection],
        mission_metadata=MissionMetadata(MISSION_ID),
    )

    slimm_service.upload_metadata(mission=mission)

    assert blob_service.blob_exists(
        path_to_blob=Path(f"{MISSION_ID}/{MISSION_ID}_META.json")
    ), "Failed to upload mission metadata to SLIMM"
    assert blob_service.blob_exists(
        path_to_blob=Path(
            f"{MISSION_ID}/sensor_data/image/{MISSION_ID}_image_NAVI.json"
        )
    ), "Failed to upload image metadata to SLIMM"
