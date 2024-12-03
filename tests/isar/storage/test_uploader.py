import time
from datetime import datetime
from threading import Thread
from typing import List, Tuple

import pytest
from alitra import Frame, Orientation, Pose, Position

from isar.models.communication.queues.queues import Queues
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader
from robot_interface.models.inspection.inspection import ImageMetadata, Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.telemetry.mqtt_client import MqttClientInterface

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
DATA_BYTES: bytes = b"Lets say this is some image data"


@pytest.fixture
def uploader(injector) -> Uploader:
    uploader: Uploader = Uploader(
        queues=injector.get(Queues),
        storage_handlers=injector.get(List[StorageInterface]),
        mqtt_publisher=injector.get(MqttClientInterface),
    )

    # The thread is deliberately started but not joined so that it runs in the
    # background and stops when the test ends
    thread = Thread(target=uploader.run, daemon=True)
    thread.start()

    return uploader


def test_should_upload_from_queue(uploader) -> None:
    mission: Mission = Mission([])
    inspection: Inspection = Inspection(metadata=ARBITRARY_IMAGE_METADATA)

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    uploader.upload_queue.put(message)
    time.sleep(1)
    assert uploader.storage_handlers[0].blob_exists(inspection)


def test_should_retry_failed_upload_from_queue(uploader) -> None:
    mission: Mission = Mission([])
    inspection: Inspection = Inspection(metadata=ARBITRARY_IMAGE_METADATA)

    message: Tuple[Inspection, Mission] = (
        inspection,
        mission,
    )

    # Need it to fail so that it retries
    uploader.storage_handlers[0].will_fail = True
    uploader.upload_queue.put(message)
    time.sleep(1)

    # Should not upload, instead raise StorageException
    assert not uploader.storage_handlers[0].blob_exists(inspection)
    uploader.storage_handlers[0].will_fail = False
    time.sleep(3)

    # After 3 seconds, it should have retried and now it should be successful
    assert uploader.storage_handlers[0].blob_exists(inspection)
