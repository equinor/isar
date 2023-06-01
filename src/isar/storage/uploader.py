import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import Empty, Queue
from typing import List

from injector import inject

from isar.config.settings import settings
from isar.models.communication.queues import Queues
from robot_interface.models.mission.mission import Mission
from isar.storage.storage_interface import StorageException, StorageInterface
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.utilities.json_service import EnhancedJSONEncoder


@dataclass
class UploaderQueueItem:
    inspection: Inspection
    mission: Mission
    storage_handler: StorageInterface
    _retry_count: int
    _next_retry_time: datetime = datetime.utcnow()

    def increment_retry(self, max_wait_time: int) -> None:
        self._retry_count += 1
        seconds_until_retry: int = min(2**self._retry_count, max_wait_time)
        self._next_retry_time = datetime.utcnow() + timedelta(
            seconds=seconds_until_retry
        )

    def get_retry_count(self) -> int:
        return self._retry_count

    def is_ready_for_upload(self) -> bool:
        return datetime.utcnow() >= self._next_retry_time

    def seconds_until_retry(self) -> int:
        return max(0, int((self._next_retry_time - datetime.utcnow()).total_seconds()))


class Uploader:
    @inject
    def __init__(
        self,
        queues: Queues,
        storage_handlers: List[StorageInterface],
        mqtt_publisher: MqttClientInterface,
        max_wait_time: int = settings.UPLOAD_FAILURE_MAX_WAIT,
        max_retry_attempts: int = settings.UPLOAD_FAILURE_ATTEMPTS_LIMIT,
    ) -> None:
        """Initializes the uploader.

        Parameters
        ----------
        queues : Queues
            Queues used for cross-thread communication.
        storage_handlers : List[StorageInterface]
            List of handlers for different upload options
        max_wait_time : float
            The maximum wait time between two retries (exponential backoff)
        max_retry_attempts : int
            Maximum attempts to retry an upload when it fails
        """
        self.upload_queue: Queue = queues.upload_queue
        self.storage_handlers: List[StorageInterface] = storage_handlers
        self.mqtt_publisher = mqtt_publisher

        self.max_wait_time = max_wait_time
        self.max_retry_attempts = max_retry_attempts
        self._internal_upload_queue: List[UploaderQueueItem] = []

        self.logger = logging.getLogger("uploader")

    def run(self) -> None:
        self.logger.info("Started uploader")
        while True:
            inspection: Inspection
            mission: Mission
            try:
                if self._internal_upload_queue:
                    self._process_upload_queue()

                inspection, mission = self.upload_queue.get(timeout=1)

                if not mission:
                    self.logger.warning(
                        "Failed to upload missing mission from upload queue"
                    )
                    continue

                # If new item from thread queue, add one per handler to internal queue:
                for storage_handler in self.storage_handlers:
                    new_item: UploaderQueueItem = UploaderQueueItem(
                        inspection, mission, storage_handler, _retry_count=-1
                    )
                    self._internal_upload_queue.append(new_item)
            except Empty:
                continue

    def _upload(self, upload_item: UploaderQueueItem) -> str:
        inspection_path = ""
        try:
            inspection_path = upload_item.storage_handler.store(
                inspection=upload_item.inspection, mission=upload_item.mission
            )
            self.logger.info(
                f"Storage handler: {type(upload_item.storage_handler).__name__} "
                f"uploaded inspection {str(upload_item.inspection.id)[:8]}"
            )
            self._internal_upload_queue.remove(upload_item)
        except StorageException:
            if upload_item.get_retry_count() < self.max_retry_attempts:
                upload_item.increment_retry(self.max_wait_time)
                self.logger.warning(
                    f"Storage handler: {type(upload_item.storage_handler).__name__} "
                    f"failed to upload inspection: "
                    f"{str(upload_item.inspection.id)[:8]}. "
                    f"Retrying in {upload_item.seconds_until_retry()}s."
                )
            else:
                self._internal_upload_queue.remove(upload_item)
                self.logger.error(
                    f"Storage handler: {type(upload_item.storage_handler).__name__} "
                    f"exceeded max retries to upload inspection: "
                    f"{str(upload_item.inspection.id)[:8]}. Aborting upload."
                )
        return inspection_path

    def _process_upload_queue(self) -> None:
        ready_items: List[UploaderQueueItem] = [
            x for x in self._internal_upload_queue if x.is_ready_for_upload()
        ]
        for item in ready_items:
            inspection_path = self._upload(item)
            self._publish_inspection_path(
                inspection=item.inspection, inspection_path=inspection_path
            )

    def _publish_inspection_path(
        self, inspection: Inspection, inspection_path: str
    ) -> None:
        """Publishes the image url to the MQTT Broker"""
        if not self.mqtt_publisher:
            return
        payload: str = json.dumps(
            {
                "isar_id": settings.ISAR_ID,
                "robot_name": settings.ROBOT_NAME,
                "step_id": inspection.id,
                "inspection_path": inspection_path,
                "timestamp": datetime.utcnow(),
            },
            cls=EnhancedJSONEncoder,
        )
        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_INSPECTION_RESULT,
            payload=payload,
            retain=False,
        )
