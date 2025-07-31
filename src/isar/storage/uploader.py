import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from queue import Empty, Queue
from threading import Event
from typing import List, Union

from isar.config.settings import settings
from isar.models.events import Events
from isar.storage.storage_interface import StorageException, StorageInterface
from robot_interface.models.inspection.inspection import (
    Inspection,
    InspectionBlob,
    InspectionValue,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.telemetry.payloads import (
    InspectionResultPayload,
    InspectionValuePayload,
)
from robot_interface.utilities.json_service import EnhancedJSONEncoder


@dataclass
class UploaderQueueItem:
    inspection: Inspection
    mission: Mission


@dataclass
class ValueItem(UploaderQueueItem):
    inspection: InspectionValue


@dataclass
class BlobItem(UploaderQueueItem):
    inspection: InspectionBlob
    storage_handler: StorageInterface
    _retry_count: int
    _next_retry_time: datetime = datetime.now(timezone.utc)

    def increment_retry(self, max_wait_time: int) -> None:
        self._retry_count += 1
        seconds_until_retry: int = min(2**self._retry_count, max_wait_time)
        self._next_retry_time = datetime.now(timezone.utc) + timedelta(
            seconds=seconds_until_retry
        )

    def get_retry_count(self) -> int:
        return self._retry_count

    def is_ready_for_upload(self) -> bool:
        return datetime.now(timezone.utc) >= self._next_retry_time

    def seconds_until_retry(self) -> int:
        return max(
            0, int((self._next_retry_time - datetime.now(timezone.utc)).total_seconds())
        )


class Uploader:
    def __init__(
        self,
        events: Events,
        storage_handlers: List[StorageInterface],
        mqtt_publisher: MqttClientInterface,
        max_wait_time: int = settings.UPLOAD_FAILURE_MAX_WAIT,
        max_retry_attempts: int = settings.UPLOAD_FAILURE_ATTEMPTS_LIMIT,
    ) -> None:
        """Initializes the uploader.

        Parameters
        ----------
        events : Events
            Events used for cross-thread communication.
        storage_handlers : List[StorageInterface]
            List of handlers for different upload options
        max_wait_time : float
            The maximum wait time between two retries (exponential backoff)
        max_retry_attempts : int
            Maximum attempts to retry an upload when it fails
        """
        self.upload_queue: Queue = events.upload_queue
        self.storage_handlers: List[StorageInterface] = storage_handlers
        self.mqtt_publisher = mqtt_publisher

        self.max_wait_time = max_wait_time
        self.max_retry_attempts = max_retry_attempts
        self._internal_upload_queue: List[UploaderQueueItem] = []

        self.signal_thread_quitting: Event = Event()

        self.logger = logging.getLogger("uploader")

    def stop(self) -> None:
        self.signal_thread_quitting.set()

    def run(self) -> None:
        self.logger.info("Started uploader")
        while not self.signal_thread_quitting.wait(0):
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

                new_item: UploaderQueueItem
                if isinstance(inspection, InspectionValue):
                    new_item = ValueItem(inspection, mission)
                    self._internal_upload_queue.append(new_item)

                elif isinstance(inspection, InspectionBlob):
                    # If new item from thread queue, add one per handler to internal queue:
                    for storage_handler in self.storage_handlers:
                        new_item = BlobItem(
                            inspection, mission, storage_handler, _retry_count=-1
                        )
                        self._internal_upload_queue.append(new_item)
                else:
                    self.logger.warning(
                        f"Unable to add UploaderQueueItem as its type {type(inspection).__name__} is unsupported"
                    )
            except Empty:
                continue

    def _upload(self, item: BlobItem) -> Union[str, dict]:
        inspection_path: Union[str, dict] = ""
        try:
            inspection_path = item.storage_handler.store(
                inspection=item.inspection, mission=item.mission
            )
            self.logger.info(
                f"Storage handler: {type(item.storage_handler).__name__} "
                f"uploaded inspection {str(item.inspection.id)[:8]}"
            )
            self._internal_upload_queue.remove(item)
        except StorageException:
            if item.get_retry_count() < self.max_retry_attempts:
                item.increment_retry(self.max_wait_time)
                self.logger.warning(
                    f"Storage handler: {type(item.storage_handler).__name__} "
                    f"failed to upload inspection: "
                    f"{str(item.inspection.id)[:8]}. "
                    f"Retrying in {item.seconds_until_retry()}s."
                )
            else:
                self.logger.error(
                    f"Storage handler: {type(item.storage_handler).__name__} "
                    f"exceeded max retries to upload inspection: "
                    f"{str(item.inspection.id)[:8]}. Aborting upload."
                )
                self._internal_upload_queue.remove(item)
        return inspection_path

    def _process_upload_queue(self) -> None:
        def should_upload(_item):
            if isinstance(_item, ValueItem):
                return True
            if _item.is_ready_for_upload():
                return True
            return False

        ready_items: List[UploaderQueueItem] = [
            item for item in self._internal_upload_queue if should_upload(item)
        ]
        for item in ready_items:
            if isinstance(item, ValueItem):
                self._publish_inspection_value(item.inspection)
                self.logger.info(
                    f"Published value for inspection {str(item.inspection.id)[:8]}"
                )
                self._internal_upload_queue.remove(item)
            elif isinstance(item, BlobItem):
                inspection_path = self._upload(item)
                self._publish_inspection_result(
                    inspection=item.inspection, inspection_path=inspection_path
                )
            else:
                self.logger.warning(
                    f"Unable to process upload item as its type {type(item).__name__} is not supported"
                )

    def _publish_inspection_value(self, inspection: InspectionValue) -> None:
        if not self.mqtt_publisher:
            return

        if not isinstance(inspection, InspectionValue):
            logging.warning(
                f"Excpected type InspectionValue but got {type(inspection).__name__} instead"
            )
            return

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
        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_INSPECTION_VALUE,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def _publish_inspection_result(
        self, inspection: InspectionBlob, inspection_path: Union[str, dict]
    ) -> None:
        """Publishes the reference of the inspection result to the MQTT Broker
        along with the analysis type
        """
        if not self.mqtt_publisher:
            return

        payload: InspectionResultPayload = InspectionResultPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            inspection_id=inspection.id,
            inspection_path=inspection_path,
            installation_code=settings.PLANT_SHORT_NAME,
            tag_id=inspection.metadata.tag_id,
            inspection_type=type(inspection).__name__,
            inspection_description=inspection.metadata.inspection_description,
            timestamp=inspection.metadata.start_time,
        )
        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_INSPECTION_RESULT,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )
