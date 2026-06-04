import json
import time
from typing import Callable, Tuple
from uuid import uuid4

from alitra import Frame, Orientation, Pose, Position

from isar.modules import ApplicationContainer
from isar.storage.uploader import Uploader
from robot_interface.models.inspection.inspection import Inspection, InspectionBlob
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage
from tests.test_mocks.blob_storage import StorageEmptyBlobPathsFake, StorageFake
from tests.test_mocks.inspection import stub_image_metadata
from tests.test_mocks.mqtt_client import MqttPublisherFake
from tests.test_mocks.state_machine_mocks import UploaderThreadMock

MISSION_ID = "some-mission-id"


def _wait_until(
    predicate: Callable[[], bool], timeout: float = 5.0, interval: float = 0.01
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"Timed out after {timeout}s waiting for predicate")


def test_should_upload_from_queue(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

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
    mission: Mission = Mission(name="Dummy misson", tasks=[take_image_task])

    assert isinstance(mission.tasks[0], TakeImage)
    inspection = InspectionBlob(
        metadata=stub_image_metadata(), id=mission.tasks[0].inspection_id
    )

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    uploader: Uploader = container.uploader()
    storage_handler: StorageFake = uploader.storage_handlers[0]  # type: ignore

    uploader.upload_queue.put(message)
    _wait_until(lambda: inspection in storage_handler.stored_inspections)


def test_should_retry_failed_upload_from_queue(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

    INSPECTION_ID = "123-456"
    inspection = InspectionBlob(metadata=stub_image_metadata(), id=INSPECTION_ID)
    mission: Mission = Mission(name="Dummy Mission")

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    uploader: Uploader = container.uploader()
    storage_handler: StorageFake = uploader.storage_handlers[0]  # type: ignore

    # Need it to fail so that it retries
    storage_handler.will_fail = True
    uploader.upload_queue.put(message)
    # Fixed wait: asserting absence of upload requires a real elapsed window
    time.sleep(1)

    # Should not upload, instead raise StorageException
    assert not storage_handler.blob_exists(inspection)
    storage_handler.will_fail = False

    # Retry succeeds once exponential backoff elapses
    _wait_until(lambda: storage_handler.blob_exists(inspection), timeout=5.0)


def test_should_not_publish_when_blob_paths_are_empty(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

    mission: Mission = Mission(name="Dummy mission")
    inspection: Inspection = InspectionBlob(
        metadata=stub_image_metadata(), id="blob-empty"
    )

    uploader: Uploader = container.uploader()

    storage_handler: StorageEmptyBlobPathsFake() = StorageEmptyBlobPathsFake()  # type: ignore
    uploader.storage_handlers[0] = storage_handler

    mqtt_fake = MqttPublisherFake()
    uploader.mqtt_publisher = mqtt_fake

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )
    uploader.upload_queue.put(message)
    _wait_until(lambda: inspection in storage_handler.stored)

    # Brief quiet period to confirm no MQTT publish follows the store
    time.sleep(0.1)
    assert len(mqtt_fake.published) == 0


def _put_inspection_with_analysis_types(
    container: ApplicationContainer,
    analysis_types: list[str] | None,
) -> MqttPublisherFake:
    inspection = InspectionBlob(
        metadata=stub_image_metadata(analysis_types=analysis_types), id=str(uuid4())
    )
    mission = Mission(name="m")

    uploader: Uploader = container.uploader()
    mqtt_fake = MqttPublisherFake()
    uploader.mqtt_publisher = mqtt_fake

    message: Tuple[Inspection, Mission] = (inspection, mission)
    uploader.upload_queue.put(message)
    return mqtt_fake


def test_publishes_required_analysis_when_present(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()
    mqtt_fake = _put_inspection_with_analysis_types(
        container, ["anonymize", "thermal-reading"]
    )
    _wait_until(lambda: mqtt_fake.count() == 1)

    payload = json.loads(mqtt_fake.last()["payload"])
    assert payload["required_analysis"] == ["anonymize", "thermal-reading"]


def test_publishes_null_required_analysis_when_absent(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()
    mqtt_fake = _put_inspection_with_analysis_types(container, None)
    _wait_until(lambda: mqtt_fake.count() == 1)

    payload = json.loads(mqtt_fake.last()["payload"])
    assert payload["required_analysis"] is None
