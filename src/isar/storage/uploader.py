import logging
import time

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue, props_expiry
from isar.storage.storage_interface import (
    BlobStoragePath,
    LocalStoragePath,
    StorageException,
    StorageInterface,
    StoragePaths,
)
from robot_interface.models.inspection.inspection import (
    Inspection,
    InspectionBlob,
    InspectionValue,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.telemetry.payloads import (
    InspectionResultPayload,
    InspectionValuePayload,
)


def has_empty_blob_storage_path(storage_paths: StoragePaths) -> bool:
    for path in (storage_paths.data_path, storage_paths.metadata_path):
        for value in (path.storage_account, path.blob_container, path.blob_name):
            if not (value and value.strip()):
                return True
    return False


class Uploader:
    def __init__(
        self,
        storage_handlers: list[StorageInterface],
        mqtt_queue: MQTTQueue,
    ) -> None:
        """Initializes the uploader.

        Parameters
        ----------
        storage_handlers : List[StorageInterface]
            List of handlers for different upload options
        mqtt_publisher : MqttClientInterface
            The client used to publish results to MQTT
        """
        self.storage_handlers: list[StorageInterface] = storage_handlers
        self.mqtt_queue: MQTTQueue = mqtt_queue
        self.logger = logging.getLogger("uploader")

    def upload_inspection(self, inspection: Inspection, mission: Mission) -> None:
        if isinstance(inspection, InspectionValue):
            _publish_inspection_value(self.mqtt_queue, inspection)
            self.logger.info(f"Published value for inspection {str(inspection.id)[:8]}")

        elif isinstance(inspection, InspectionBlob):
            for storage_handler in self.storage_handlers:
                inspection_paths: StoragePaths | None = _upload(
                    self.logger, storage_handler, inspection, mission
                )

                if inspection_paths is None:
                    continue

                if isinstance(inspection_paths.data_path, LocalStoragePath):
                    self.logger.info("Skipping publishing when using local storage")
                elif isinstance(
                    inspection_paths.data_path, BlobStoragePath
                ) and has_empty_blob_storage_path(inspection_paths):
                    self.logger.warning(
                        "Skipping publishing: Blob storage paths are empty for inspection %s",
                        str(inspection.id)[:8],
                    )
                else:
                    _publish_inspection_result(
                        self.mqtt_queue,
                        inspection=inspection,
                        inspection_paths=inspection_paths,
                        mission=mission,
                    )

        else:
            self.logger.warning(
                f"Unable to add upload item as its type {type(inspection).__name__} is unsupported"
            )


def _upload(
    logger: logging.Logger,
    storage_handler: StorageInterface,
    inspection: Inspection,
    mission: Mission,
) -> StoragePaths | None:
    inspection_paths: StoragePaths
    upload_attempts: int = 0
    while upload_attempts < settings.UPLOAD_FAILURE_ATTEMPTS_LIMIT:
        try:
            inspection_paths = storage_handler.store(
                inspection=inspection, mission=mission
            )
            logger.info(
                f"Storage handler: {type(storage_handler).__name__} "
                f"uploaded inspection {str(inspection.id)[:8]}"
            )
            return inspection_paths
        except StorageException:
            upload_attempts += 1

            if upload_attempts < settings.UPLOAD_FAILURE_ATTEMPTS_LIMIT:
                sleep_length = min(2**upload_attempts, settings.UPLOAD_FAILURE_MAX_WAIT)
                logger.warning(
                    f"Storage handler: {type(storage_handler).__name__} "
                    f"failed to upload inspection: "
                    f"{str(inspection.id)[:8]}. "
                    f"Retrying in {sleep_length}s."
                )
                time.sleep(sleep_length)
    logger.error(
        f"Storage handler: {type(storage_handler).__name__} "
        f"exceeded max retries to upload inspection: "
        f"{str(inspection.id)[:8]}. Aborting upload."
    )
    return None


def _publish_inspection_value(
    mqtt_queue: MQTTQueue, inspection: InspectionValue
) -> None:
    payload: InspectionValuePayload = InspectionValuePayload(
        isar_id=settings.ISAR_ID,
        robot_name=settings.ROBOT_NAME,
        inspection_id=inspection.id,
        installation_code=settings.PLANT_SHORT_NAME,
        tag_id=inspection.metadata.tag_id,
        inspection_type=type(inspection).__name__,
        inspection_description=inspection.metadata.inspection_description,
        value=inspection.value,
        unit=inspection.unit,
        x=inspection.metadata.robot_pose.position.x,
        y=inspection.metadata.robot_pose.position.y,
        z=inspection.metadata.robot_pose.position.z,
        timestamp=inspection.metadata.start_time,
    )
    mqtt_queue.publish(
        topic=settings.TOPIC_ISAR_INSPECTION_VALUE,
        payload=payload.model_dump_json(),
        qos=1,
        retain=True,
        properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
    )


def _publish_inspection_result(
    mqtt_queue: MQTTQueue,
    inspection: InspectionBlob,
    inspection_paths: StoragePaths[BlobStoragePath],
    mission: Mission,
) -> None:
    payload: InspectionResultPayload = InspectionResultPayload(
        isar_id=settings.ISAR_ID,
        robot_name=settings.ROBOT_NAME,
        inspection_id=inspection.id,
        mission_id=mission.id,
        blob_storage_data_path=inspection_paths.data_path,
        blob_storage_metadata_path=inspection_paths.metadata_path,
        installation_code=settings.PLANT_SHORT_NAME,
        tag_id=inspection.metadata.tag_id,
        inspection_type=type(inspection).__name__,
        inspection_description=inspection.metadata.inspection_description,
        required_analysis=inspection.metadata.analysis_types,
        timestamp=inspection.metadata.start_time,
        robot_pose=inspection.metadata.robot_pose,
        target_position=inspection.metadata.target_position,
    )
    mqtt_queue.publish(
        topic=settings.TOPIC_ISAR_INSPECTION_RESULT,
        payload=payload.model_dump_json(),
        qos=1,
        retain=True,
        properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
    )
