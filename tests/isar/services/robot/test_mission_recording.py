"""Essential mission recording lifecycle and Blob publication contracts."""

import asyncio
import json
from pathlib import Path
from typing import Any, BinaryIO
from unittest.mock import Mock

import pytest
from azure.core.exceptions import ResourceExistsError
from pytest_mock import MockerFixture

from isar.robot.robot_service import RobotService
from isar.storage.recording_publisher import BlobRecordingPublisher
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage
from robot_interface.recording_models import CameraRecording, RecordingSession
from robot_interface.recording_publisher import RecordingArtifact
from tests.test_mocks.inspection import stub_pose


def recording_mission() -> Mission:
    return Mission(
        id="recording-mission",
        name="Recording",
        tasks=[
            TakeImage(id="image", robot_pose=stub_pose(), target=stub_pose().position)
        ],
    )


def test_start_only_after_robot_confirmation(
    mocked_robot_service: RobotService, mocker: MockerFixture
) -> None:
    service = mocked_robot_service
    recorder = service.mission_recorder = Mock()
    start = mocker.patch(
        "isar.robot.robot_service.robot_start_mission",
        return_value=ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="failed",
        ),
    )
    assert not service._start_mission_handler(recording_mission())
    recorder.start.assert_not_called()
    start.return_value = None
    assert service._start_mission_handler(recording_mission())
    recorder.start.assert_called_once_with("recording-mission")


@pytest.mark.parametrize("recorder_available", [False, True])
def test_mission_starts_when_recording_is_unavailable(
    mocked_robot_service: RobotService, mocker: MockerFixture, recorder_available: bool
) -> None:
    service = mocked_robot_service
    recorder = Mock()
    recorder.start.side_effect = RuntimeError("disk unavailable")
    service.mission_recorder = recorder if recorder_available else None
    mocker.patch("isar.robot.robot_service.robot_start_mission", return_value=None)
    assert service._start_mission_handler(recording_mission())


def test_pause_resume_keeps_one_logical_recording(
    mocked_robot_service: RobotService, mocker: MockerFixture
) -> None:
    service = mocked_robot_service
    recorder = service.mission_recorder = Mock()
    mocker.patch("isar.robot.robot_service.robot_pause_mission", return_value=None)
    mocker.patch("isar.robot.robot_service.robot_resume_mission", return_value=None)
    service._start_recording("mission")
    service._pause_mission_handler()
    service._resume_mission_handler()
    recorder.start.assert_called_once_with("mission")
    recorder.stop.assert_not_called()


def test_successful_stop_without_monitor_finalizes_recording(
    mocked_robot_service: RobotService, mocker: MockerFixture
) -> None:
    service = mocked_robot_service
    recorder = service.mission_recorder = Mock()
    service._start_recording("mission")
    mocker.patch("isar.robot.robot_service.robot_stop_mission", return_value=None)
    asyncio.run(service._stop_mission_handler(None))
    recorder.stop.assert_called_once_with("mission", False)


def test_terminal_monitor_stops_correct_mission(
    mocked_robot_service: RobotService, mocker: MockerFixture
) -> None:
    service = mocked_robot_service
    recorder = service.mission_recorder = Mock()
    mission = recording_mission()
    service._start_recording("newer-mission")
    mocker.patch(
        "isar.robot.robot_service.robot_monitor_mission",
        return_value=(None, mission, False),
    )
    asyncio.run(service._monitor_mission_handler(mission))
    recorder.stop.assert_called_once_with(mission.id, False)
    assert service.recording_mission_id == "newer-mission"


@pytest.fixture
def publisher() -> BlobRecordingPublisher:
    publisher = BlobRecordingPublisher("robot")
    publisher._container = Mock()
    return publisher


def test_recording_storage_reuses_inspection_connection_lazily(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "isar.storage.recording_publisher.settings.BLOB_STORAGE_CONNECTION_STRING_DATA",
        "inspection-storage",
    )
    create_client = mocker.patch(
        "isar.storage.recording_publisher.BlobServiceClient.from_connection_string"
    )
    publisher = BlobRecordingPublisher("robot")
    create_client.assert_not_called()

    container = publisher._container

    create_client.assert_called_once_with("inspection-storage")
    create_client.return_value.get_container_client.assert_called_once_with(
        "mission-recordings"
    )
    assert container is publisher._container
    create_client.assert_called_once()


def test_video_upload_failure_preserves_source_and_retry_uses_stable_path(
    publisher: BlobRecordingPublisher, tmp_path: Path
) -> None:
    source = tmp_path / "vendor-export.webm"
    source.write_bytes(b"completed footage")
    artifact = RecordingArtifact("front", "camera-key", source, "video/webm")
    container: Any = publisher._container
    container.create_container.side_effect = ResourceExistsError()
    container.upload_blob.side_effect = OSError("unavailable")

    with pytest.raises(OSError):
        asyncio.run(publisher.publish_video("mission", artifact))
    assert source.read_bytes() == b"completed footage"

    uploads: list[tuple[str, bytes, dict[str, Any]]] = []

    def capture_upload(name: str, data: BinaryIO, **options: Any) -> None:
        uploads.append((name, data.read(), options))

    container.upload_blob.side_effect = capture_upload
    first = asyncio.run(publisher.publish_video("mission", artifact))
    second = asyncio.run(publisher.publish_video("mission", artifact))

    assert first == second == "mission/camera-key.webm"
    assert source.read_bytes() == b"completed footage"
    assert all(
        name == first and data == b"completed footage" for name, data, _ in uploads
    )
    assert all(options["overwrite"] for _, _, options in uploads)
    assert uploads[0][2]["content_settings"].content_type == "video/webm"


def test_manifest_translates_references_and_preserves_driver_state(
    publisher: BlobRecordingPublisher,
) -> None:
    class DriverCamera(CameraRecording):
        source_codec: str

    session = RecordingSession[DriverCamera](
        run_id="mission",
        status="Ready",
        cameras={
            "front": DriverCamera(
                camera_id="front",
                key="front",
                status="Ready",
                source_codec="H264",
                artifact_reference="mission/front.mp4",
            )
        },
    )
    original = session.model_dump()

    asyncio.run(publisher.publish_session(session))

    container: Any = publisher._container
    name, content = container.upload_blob.call_args.args
    manifest = json.loads(content)
    camera = manifest["cameras"]["front"]
    assert name == "mission/session.json"
    assert manifest["isarId"] == "robot"
    assert camera["sourceCodec"] == "H264"
    assert camera["blobName"] == "mission/front.mp4"
    assert "artifactReference" not in camera
    assert session.model_dump() == original
