import time
from datetime import datetime
from typing import Tuple

from alitra import Frame, Orientation, Pose, Position

from isar.modules import ApplicationContainer
from isar.storage.uploader import Uploader
from robot_interface.models.inspection.inspection import ImageMetadata, Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage
from tests.isar.state_machine.test_state_machine import UploaderThreadMock
from tests.mocks.blob_storage import StorageMock

MISSION_ID = "some-mission-id"
ARBITRARY_IMAGE_METADATA = ImageMetadata(
    start_time=datetime.now(),
    pose=Pose(
        Position(0, 0, 0, Frame("asset")),
        Orientation(x=0, y=0, z=0, w=1, frame=Frame("asset")),
        Frame("asset"),
    ),
    file_type="jpg",
)


def test_should_upload_from_queue(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

    take_image_task = TakeImage()
    mission: Mission = Mission(name="Dummy misson", tasks=[take_image_task])

    assert isinstance(mission.tasks[0], TakeImage)
    inspection = Inspection(
        metadata=ARBITRARY_IMAGE_METADATA, id=mission.tasks[0].inspection_id
    )

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    uploader: Uploader = container.uploader()

    uploader.upload_queue.put(message)
    time.sleep(0.01)

    storage_handler: StorageMock = uploader.storage_handlers[0]  # type: ignore
    assert inspection in storage_handler.stored_inspections


def test_should_retry_failed_upload_from_queue(
    container: ApplicationContainer, uploader_thread: UploaderThreadMock
) -> None:
    uploader_thread.start()

    INSPECTION_ID = "123-456"
    inspection = Inspection(metadata=ARBITRARY_IMAGE_METADATA, id=INSPECTION_ID)
    mission: Mission = Mission(name="Dummy Mission")

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    uploader: Uploader = container.uploader()
    storage_handler: StorageMock = uploader.storage_handlers[0]  # type: ignore

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
