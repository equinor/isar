"""Azure publication for the platform's recording playback contract."""

import asyncio
import logging
from datetime import UTC, datetime
from functools import cached_property
from pathlib import PurePosixPath
from time import monotonic
from typing import Any

from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue, props_expiry
from isar.storage.storage_interface import BlobStoragePath
from robot_interface.recording_models import CameraRecording, RecordingSession
from robot_interface.recording_publisher import RecordingArtifact
from robot_interface.telemetry.payloads import InspectionResultPayload

logger = logging.getLogger(__name__)


class BlobRecordingPublisher:
    """Publish recordings without exposing Azure clients or blob paths to drivers."""

    def __init__(self, isar_id: str, mqtt_queue: MQTTQueue) -> None:
        self.isar_id = isar_id
        self.mqtt_queue = mqtt_queue

    @cached_property
    def _container(self) -> ContainerClient:
        return BlobServiceClient.from_connection_string(
            settings.BLOB_STORAGE_CONNECTION_STRING_DATA
        ).get_container_client(settings.BLOB_CONTAINER)

    async def publish_video(self, mission_id: str, artifact: RecordingArtifact) -> str:
        blob_name = f"{mission_id}/{artifact.artifact_id}{artifact.path.suffix}"
        started = monotonic()
        logger.debug(
            "Recording upload started mission_id=%s camera_id=%s artifact_id=%s",
            mission_id,
            artifact.camera_id,
            artifact.artifact_id,
        )
        upload = asyncio.create_task(
            asyncio.to_thread(self._upload_video, artifact, blob_name)
        )
        try:
            await asyncio.wait_for(asyncio.shield(upload), timeout=300)
        except BaseException:
            await asyncio.shield(asyncio.gather(upload, return_exceptions=True))
            raise
        logger.debug(
            "Recording upload completed mission_id=%s camera_id=%s artifact_id=%s elapsed_seconds=%.2f",
            mission_id,
            artifact.camera_id,
            artifact.artifact_id,
            monotonic() - started,
        )
        return blob_name

    def _upload_video(self, artifact: RecordingArtifact, blob_name: str) -> None:
        with artifact.path.open("rb") as data:
            self._container.upload_blob(
                blob_name,
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=artifact.content_type),
                connection_timeout=10,
                read_timeout=30,
                retry_total=2,
            )

    async def publish_session[Camera: CameraRecording](
        self, session: RecordingSession[Camera]
    ) -> None:
        snapshot = session.model_copy(deep=True)
        snapshot.isar_id = self.isar_id
        for camera in snapshot.cameras.values():
            if camera.artifact_reference:
                camera.blob_name = camera.artifact_reference
            camera.artifact_reference = None
        document = snapshot.model_dump_json(
            by_alias=True, exclude_none=True, serialize_as_any=True
        ).encode()
        blob_name = f"{session.run_id}/session.json"
        await asyncio.wait_for(
            asyncio.to_thread(self._upload_manifest, blob_name, document), timeout=60
        )
        if snapshot.status in ("Ready", "Expired"):
            for camera in snapshot.cameras.values():
                if camera.status == "Ready" and camera.blob_name:
                    self._publish_inspection_result(snapshot, camera, camera.blob_name)

    def _publish_inspection_result(
        self,
        session: RecordingSession[Any],
        camera: CameraRecording,
        blob_name: str,
    ) -> None:
        """Announce a finished camera recording to SARA as a video inspection."""
        started_at = (
            datetime.fromisoformat(session.started_at) if session.started_at else None
        )
        ended_at = (
            datetime.fromisoformat(session.ended_at) if session.ended_at else None
        )
        payload = InspectionResultPayload(
            isar_id=self.isar_id,
            robot_name=settings.ROBOT_NAME,
            inspection_id=f"{session.run_id}-{camera.key}",
            mission_id=session.run_id,
            mission_name="",
            blob_storage_data_path=BlobStoragePath(
                storage_account=settings.BLOB_STORAGE_ACCOUNT_DATA,
                blob_container=settings.BLOB_CONTAINER,
                blob_name=blob_name,
            ),
            installation_code=settings.PLANT_SHORT_NAME,
            inspection_type="Video",
            inspection_description=f"Mission recording from camera {camera.key}",
            timestamp=started_at or datetime.now(UTC),
            file_type=PurePosixPath(blob_name).suffix.lstrip("."),
            duration=(
                (ended_at - started_at).total_seconds()
                if started_at and ended_at
                else None
            ),
        )
        self.mqtt_queue.publish(
            topic=settings.TOPIC_ISAR_INSPECTION_RESULT,
            payload=payload.model_dump_json(),
            qos=1,
            retain=True,
            properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
        )

    def _upload_manifest(self, blob_name: str, document: bytes) -> None:
        self._container.upload_blob(
            blob_name,
            document,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
            connection_timeout=10,
            read_timeout=30,
            retry_total=2,
        )
