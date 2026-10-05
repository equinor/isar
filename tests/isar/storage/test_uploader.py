import json
from uuid import uuid4

from alitra import Frame, Orientation, Pose, Position
from pytest_mock import MockerFixture

from isar.config.settings import settings
from isar.storage.blob_storage import BlobStorage
from isar.storage.storage_interface import StorageException
from isar.storage.uploader import Uploader
from robot_interface.models.inspection.inspection import Inspection, InspectionBlob
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage
from tests.test_mocks.blob_storage import StorageEmptyBlobPathsFake, StorageFake
from tests.test_mocks.inspection import (
    stub_acoustic_measurement_metadata,
    stub_image_metadata,
    stub_inspection_value,
)

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


def test_publishes_inspection_metadata(uploader: Uploader) -> None:
    inspection = InspectionBlob(metadata=stub_image_metadata(), id=str(uuid4()))
    mission = Mission(id="mission-id", name="Perimeterrunde - Nordsiden")

    uploader.upload_inspection(inspection, mission)

    payload = json.loads(uploader.mqtt_queue.get().payload)
    assert payload["mission_name"] == mission.name
    assert payload["file_type"] == inspection.metadata.file_type
    assert payload["duration"] is None
    assert payload["acoustic_metadata"] is None
    assert "blob_storage_metadata_path" not in payload


def test_publishes_acoustic_metadata(uploader: Uploader) -> None:
    metadata = stub_acoustic_measurement_metadata()
    inspection = InspectionBlob(metadata=metadata, id=str(uuid4()))

    uploader.upload_inspection(inspection, Mission(id="mission-id", name="Mission"))

    payload = json.loads(uploader.mqtt_queue.get().payload)
    assert payload["duration"] == metadata.duration
    assert payload["acoustic_metadata"] == {
        "snr_value": metadata.snr_value,
        "leak_rate": metadata.leak_rate,
        "leak_rate_unit": metadata.leak_rate_unit,
        "sound_pressure_level_at_sensor_db": metadata.sound_pressure_level_at_sensor_db,
        "sound_pressure_level_at_source_db": metadata.sound_pressure_level_at_source_db,
        "distance_to_source": metadata.distance_to_source,
        "result": metadata.result,
        "frequency_from": metadata.frequency_from,
        "frequency_to": metadata.frequency_to,
    }


def test_uploads_scalar_as_json(uploader: Uploader, mocker: MockerFixture) -> None:
    container = mocker.Mock()
    blob = container.get_blob_client.return_value
    blob.blob_name = "scalar.json"
    mocker.patch.object(BlobStorage, "_get_container_client", return_value=container)
    uploader.storage_handlers = [BlobStorage()]
    inspection = stub_inspection_value()
    expected = inspection.model_dump(mode="json")
    expected["metadata"]["file_type"] = "json"

    uploader.upload_inspection(inspection, Mission(id="mission-id", name="Mission"))

    assert json.loads(blob.upload_blob.call_args.kwargs["data"]) == expected
    filename = container.get_blob_client.call_args.args[0]
    assert "__CO2Measurement__" in filename and filename.endswith(".json")
    assert inspection.metadata.file_type == "txt"


def test_publishes_scalar_fields_with_blob_reference(uploader: Uploader) -> None:
    inspection = stub_inspection_value()
    metadata = inspection.metadata.model_dump(mode="json")

    uploader.upload_inspection(inspection, Mission(id="mission-id", name="Mission"))

    message = uploader.mqtt_queue.get()
    assert json.loads(message.payload) == {
        "isar_id": settings.ISAR_ID,
        "robot_name": settings.ROBOT_NAME,
        "inspection_id": inspection.id,
        "blob_storage_data_path": {
            "storage_account": "acct",
            "blob_container": "cont",
            "blob_name": "blob",
        },
        "installation_code": settings.PLANT_SHORT_NAME,
        "tag_id": "CO2-001",
        "inspection_type": "CO2Measurement",
        "inspection_description": "Carbon dioxide",
        "value": 412.5,
        "unit": "ppm",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
        "timestamp": "2026-09-24T12:00:00Z",
        "robot_pose": metadata["robot_pose"],
        "target_position": metadata["target_position"],
    }
    assert (
        message.topic,
        message.qos,
        message.retain,
        message.properties.MessageExpiryInterval,
    ) == (
        settings.TOPIC_ISAR_INSPECTION_VALUE,
        1,
        True,
        settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY,
    )
    assert uploader.mqtt_queue.empty()


def test_does_not_publish_scalar_after_upload_exhaustion(
    uploader: Uploader, mocker: MockerFixture
) -> None:
    mocker.patch.object(settings, "UPLOAD_FAILURE_ATTEMPTS_LIMIT", 2)
    mocker.patch("isar.storage.uploader.time.sleep")
    store = mocker.patch.object(
        uploader.storage_handlers[0],
        "store",
        side_effect=StorageException("Upload failed"),
    )

    uploader.upload_inspection(
        stub_inspection_value(), Mission(id="mission-id", name="Mission")
    )

    assert store.call_count == 2
    assert uploader.mqtt_queue.empty()
