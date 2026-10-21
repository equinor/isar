"""Azure publication for the platform's recording playback contract."""

import asyncio
import logging
from functools import cached_property
from time import monotonic

from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings

from isar.config.settings import settings
from robot_interface.recording_models import CameraRecording, RecordingSession
from robot_interface.recording_publisher import RecordingArtifact

logger = logging.getLogger(__name__)


class BlobRecordingPublisher:
    """Publish recordings without exposing Azure clients or blob paths to drivers."""

    def __init__(self, isar_id: str) -> None:
        self.isar_id = isar_id

    @cached_property
    def _container(self) -> ContainerClient:
        return BlobServiceClient.from_connection_string(
            settings.BLOB_STORAGE_CONNECTION_STRING_DATA
        ).get_container_client("mission-recordings")

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
