import json
from uuid import uuid4

from alitra import Frame, Orientation, Pose, Position
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.storage.uploader import Uploader
from robot_interface.models.inspection.inspection import Inspection, InspectionBlob
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage
from tests.test_mocks.blob_storage import StorageEmptyBlobPathsFake, StorageFake
from tests.test_mocks.inspection import stub_image_metadata

MISSION_ID = "some-mission-id"


def test_should_upload_from_queue(uploader: Uploader) -> None:
    pose = Pose(
        position=Position(x=4, y=4, z=0, frame=Frame(name="asset")),
        orientation=Orientation(
            x=0, y=0, z=-0.7071068, w=0.7071068, frame=Frame(name="asset")
        ),
        frame=Frame(name="asset"),
    )

    take_image_task = TakeImage(
        id=str(uuid4()),
        robot_pose=pose,
        tag_id=str(uuid4()),
        inspection_description="test",
        target=pose.position,
        zoom=None,
    )
    mission: Mission = Mission(id="id", name="Dummy misson", tasks=[take_image_task])

    assert isinstance(mission.tasks[0], TakeImage)
    inspection = InspectionBlob(metadata=stub_image_metadata(), id=mission.tasks[0].id)

    storage_handler: StorageFake = uploader.storage_handlers[0]  # type: ignore

    uploader.upload_inspection(inspection, mission)
    assert inspection in storage_handler.stored_inspections


def test_should_retry_failed_upload_from_queue(
    uploader: Uploader, mocker: MockerFixture
) -> None:
    mocker.patch.object(settings, "UPLOAD_FAILURE_MAX_WAIT", 0.0001)
    mocker.patch.object(settings, "UPLOAD_FAILURE_ATTEMPTS_LIMIT", 4)
    INSPECTION_ID = "123-456"
    inspection = InspectionBlob(metadata=stub_image_metadata(), id=INSPECTION_ID)
    mission: Mission = Mission(id="id", name="Dummy Mission")

    storage_handler: StorageFake = uploader.storage_handlers[0]  # type: ignore

    storage_handler.failure_count = 3
    uploader.upload_inspection(inspection, mission)

    assert storage_handler.blob_exists(inspection)


def test_should_eventually_give_up_failed_upload_from_queue(
    uploader: Uploader, mocker: MockerFixture
) -> None:
    mocker.patch.object(settings, "UPLOAD_FAILURE_MAX_WAIT", 0.0001)
    mocker.patch.object(settings, "UPLOAD_FAILURE_ATTEMPTS_LIMIT", 3)
    INSPECTION_ID = "123-456"
    inspection = InspectionBlob(metadata=stub_image_metadata(), id=INSPECTION_ID)
    mission: Mission = Mission(id="id", name="Dummy Mission")

    storage_handler: StorageFake = uploader.storage_handlers[0]  # type: ignore

    storage_handler.failure_count = 5
    uploader.upload_inspection(inspection, mission)

    assert not storage_handler.blob_exists(inspection)


def test_should_not_publish_when_blob_paths_are_empty(uploader: Uploader) -> None:
    mission: Mission = Mission(id="id", name="Dummy mission")
    inspection: Inspection = InspectionBlob(
        metadata=stub_image_metadata(), id="blob-empty"
    )

    storage_handler: StorageEmptyBlobPathsFake() = StorageEmptyBlobPathsFake()  # type: ignore
    uploader.storage_handlers[0] = storage_handler

    uploader.upload_inspection(inspection, mission)
    assert inspection in storage_handler.stored

    assert uploader.mqtt_queue.qsize() == 0


def test_publishes_required_analysis_when_present(uploader: Uploader) -> None:
    inspection = InspectionBlob(
        metadata=stub_image_metadata(analysis_types=["anonymize", "thermal-reading"]),
        id=str(uuid4()),
    )
    mission = Mission(id="id", name="m")

    uploader.upload_inspection(inspection, mission)

    assert uploader.mqtt_queue.qsize() == 1

    payload = json.loads(uploader.mqtt_queue.get().payload)
    assert payload["required_analysis"] == ["anonymize", "thermal-reading"]


def test_publishes_null_required_analysis_when_absent(uploader: Uploader) -> None:
    inspection = InspectionBlob(
        metadata=stub_image_metadata(analysis_types=None), id=str(uuid4())
    )
    mission = Mission(id="id", name="m")

    uploader.upload_inspection(inspection, mission)
    assert uploader.mqtt_queue.qsize() == 1

    payload = json.loads(uploader.mqtt_queue.get().payload)
    assert payload["required_analysis"] is None
