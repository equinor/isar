import time
from datetime import datetime
from typing import Tuple
from uuid import uuid4

from alitra import Frame, Orientation, Pose, Position

from isar.modules import ApplicationContainer
from isar.storage.uploader import Uploader
from robot_interface.models.inspection.inspection import (
    ImageMetadata,
    Inspection,
    InspectionBlob,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage
from tests.test_mocks.blob_storage import StorageEmptyBlobPathsFake, StorageFake
from tests.test_mocks.mqtt_client import MqttPublisherFake
from tests.test_mocks.state_machine_mocks import UploaderThreadMock

MISSION_ID = "some-mission-id"
ARBITRARY_IMAGE_METADATA = ImageMetadata(
    start_time=datetime.now(),
    robot_pose=Pose(
        Position(0, 0, 0, Frame("asset")),
        Orientation(x=0, y=0, z=0, w=1, frame=Frame("asset")),
        Frame("asset"),
    ),
    target_position=Position(0, 0, 0, Frame("asset")),
    file_type="jpg",
)


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
        metadata=ARBITRARY_IMAGE_METADATA, id=mission.tasks[0].inspection_id
    )

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    uploader: Uploader = container.uploader()

    uploader.upload_queue.put(message)
    time.sleep(0.01)

    storage_handler: StorageFake = uploader.storage_handlers[0]  # type: ignore
    assert inspection in storage_handler.stored_inspections


def test_should_retry_failed_upload_from_queue(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

    INSPECTION_ID = "123-456"
    inspection = InspectionBlob(metadata=ARBITRARY_IMAGE_METADATA, id=INSPECTION_ID)
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
    time.sleep(1)

    # Should not upload, instead raise StorageException
    assert not storage_handler.blob_exists(inspection)
    storage_handler.will_fail = False
    time.sleep(3)

    # After some time, it should have retried and now it should be successful
    assert storage_handler.blob_exists(inspection)


def test_should_not_publish_when_blob_paths_are_empty(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

    mission: Mission = Mission(name="Dummy mission")
    inspection: Inspection = InspectionBlob(
        metadata=ARBITRARY_IMAGE_METADATA, id="blob-empty"
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
    time.sleep(1)

    assert inspection in storage_handler.stored

    assert len(mqtt_fake.published) == 0
