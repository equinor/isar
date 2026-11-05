"""Essential mission recording lifecycle and Blob publication contracts."""

import asyncio
import json
from pathlib import Path
from typing import Any, BinaryIO
from unittest.mock import Mock, call

import pytest
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


@pytest.mark.parametrize("confirmed", [False, True], ids=["rejected", "confirmed"])
def test_recording_starts_only_after_robot_confirmation(
    mocked_robot_service: RobotService, mocker: MockerFixture, confirmed: bool
) -> None:
    service = mocked_robot_service
    recorder = service.mission_recorder = Mock()
    mocker.patch(
        "isar.robot.robot_service.robot_start_mission",
        return_value=(
            None
            if confirmed
            else ErrorMessage(ErrorReason.RobotUnknownErrorException, "failed")
        ),
    )
    mission = recording_mission()

    service._start_mission_handler(mission)

    assert recorder.start.call_args_list == ([call(mission.id)] if confirmed else [])


@pytest.mark.parametrize("recorder_available", [False, True])
def test_mission_starts_when_recording_is_unavailable(
    mocked_robot_service: RobotService, mocker: MockerFixture, recorder_available: bool
) -> None:
    service = mocked_robot_service
    recorder = Mock()
    recorder.start.side_effect = RuntimeError("disk unavailable")
    service.mission_recorder = recorder if recorder_available else None
    mocker.patch("isar.robot.robot_service.robot_start_mission", return_value=None)
    mission = recording_mission()

    success = service._start_mission_handler(mission)

    assert success


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


def test_recording_storage_does_not_connect_on_construction(
    mocker: MockerFixture,
) -> None:
    create_client = mocker.patch(
        "isar.storage.recording_publisher.BlobServiceClient.from_connection_string"
    )

    BlobRecordingPublisher("robot")

    create_client.assert_not_called()


def test_recording_storage_caches_inspection_storage_connection(
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

    container = publisher._container
    cached_container = publisher._container

    create_client.assert_called_once_with("inspection-storage")
    create_client.return_value.get_container_client.assert_called_once_with(
        "mission-recordings"
    )
    assert container is cached_container


@pytest.fixture
def artifact(tmp_path: Path) -> RecordingArtifact:
    source = tmp_path / "vendor-export.webm"
    source.write_bytes(b"completed footage")
    return RecordingArtifact("front", "camera-key", source, "video/webm")


def test_video_upload_failure_preserves_source(
    publisher: BlobRecordingPublisher, artifact: RecordingArtifact
) -> None:
    container = publisher._container
    container.upload_blob.side_effect = OSError("unavailable")

    with pytest.raises(OSError, match="unavailable"):
        asyncio.run(publisher.publish_video("mission", artifact))

    assert artifact.path.read_bytes() == b"completed footage"


def test_video_upload_retry_uses_stable_path_and_content(
    publisher: BlobRecordingPublisher, artifact: RecordingArtifact
) -> None:
    container = publisher._container
    container.upload_blob.side_effect = OSError("unavailable")
    with pytest.raises(OSError, match="unavailable"):
        asyncio.run(publisher.publish_video("mission", artifact))
    uploads: list[tuple[str, bytes, bool, str]] = []

    def capture_upload(name: str, data: BinaryIO, **options: Any) -> None:
        uploads.append(
            (
                name,
                data.read(),
                options["overwrite"],
                options["content_settings"].content_type,
            )
        )

    container.upload_blob.side_effect = capture_upload

    first = asyncio.run(publisher.publish_video("mission", artifact))
    second = asyncio.run(publisher.publish_video("mission", artifact))

    assert first == second == "mission/camera-key.webm"
    assert (
        uploads
        == [("mission/camera-key.webm", b"completed footage", True, "video/webm")] * 2
    )
    assert artifact.path.read_bytes() == b"completed footage"


class DriverCamera(CameraRecording):
    source_codec: str


@pytest.fixture
def recording_session() -> RecordingSession[DriverCamera]:
    return RecordingSession[DriverCamera](
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


def test_manifest_translates_driver_references(
    publisher: BlobRecordingPublisher, recording_session: RecordingSession[DriverCamera]
) -> None:
    asyncio.run(publisher.publish_session(recording_session))

    container: Any = publisher._container
    name, content = container.upload_blob.call_args.args
    assert name == "mission/session.json"
    assert json.loads(content) == {
        "runId": "mission",
        "status": "Ready",
        "isarId": "robot",
        "gaps": [],
        "cameras": {
            "front": {
                "cameraId": "front",
                "key": "front",
                "status": "Ready",
                "sourceCodec": "H264",
                "blobName": "mission/front.mp4",
            }
        },
    }


def test_manifest_publication_preserves_driver_state(
    publisher: BlobRecordingPublisher, recording_session: RecordingSession[DriverCamera]
) -> None:
    original = recording_session.model_dump()

    asyncio.run(publisher.publish_session(recording_session))

    assert recording_session.model_dump() == original
