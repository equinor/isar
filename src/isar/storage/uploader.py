import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import Empty, Queue
from typing import List

from isar.config import config
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.storage.storage_interface import StorageException, StorageInterface
from robot_interface.models.inspection.inspection import Inspection


@dataclass
class UploaderRetryItem:
    inspection: Inspection
    mission_metadata: MissionMetadata
    storage_handler: StorageInterface
    _retry_count: int
    _next_retry_time: datetime = datetime.max

    def increment_retry(self, max_wait_time: int):
        self._retry_count += 1
        seconds_until_retry: int = min(2**self._retry_count, max_wait_time)
        self._next_retry_time = datetime.utcnow() + timedelta(
            seconds=seconds_until_retry
        )

    def get_retry_count(self) -> int:
        return self._retry_count

    def retry_is_ready(self) -> bool:
        return datetime.utcnow() >= self._next_retry_time

    def seconds_until_retry(self) -> int:
        return max(0, int((self._next_retry_time - datetime.utcnow()).total_seconds()))


class Uploader:
    def __init__(
        self,
        upload_queue: Queue,
        storage_handlers: List[StorageInterface],
        max_wait_time: int = config.getint("DEFAULT", "upload_failure_max_wait"),
        max_retry_attempts: int = config.getint(
            "DEFAULT", "upload_failure_attempts_limit"
        ),
    ) -> None:
        """Initializes the uploader.

        Parameters
        ----------
        upload_queue : Queue
            Queues used for cross-thread communication.
        storage_handlers : List[StorageInterface]
            List of handlers for different upload options
        max_wait_time : float
            The maximum wait time between two retries (exponential backoff)
        max_retry_attempts : int
            Maximum attempts to retry an upload when it fails

        """
        self.upload_queue: Queue = upload_queue
        self.storage_handlers: List[StorageInterface] = storage_handlers
        self.max_wait_time = max_wait_time
        self.max_retry_attempts = max_retry_attempts
        self.retry_queue: List[UploaderRetryItem]

        self.logger = logging.getLogger("uploader")

    def run(self) -> None:
        self.logger.info("Started uploader")
        while True:
            inspection: Inspection
            mission_metadata: MissionMetadata
            try:
                if self.retry_queue:
                    self._process_retry_queue()
                inspection, mission_metadata = self.upload_queue.get(timeout=1)
            except Empty:
                continue

            for storage_handler in self.storage_handlers:
                self._upload(
                    storage_handler, inspection, mission_metadata, retry_count=-1
                )

    def _upload(
        self,
        storage_handler: StorageInterface,
        inspection: Inspection,
        mission_metadata: MissionMetadata,
        retry_count: int,
    ):
        try:
            storage_handler.store(inspection=inspection, metadata=mission_metadata)
            self.logger.info(
                f"Storage handler: {type(storage_handler).__name__} "
                f"uploaded inspection {str(inspection.id)[:8]}"
            )
        except StorageException:
            if retry_count < self.max_retry_attempts:
                retry_item: UploaderRetryItem = UploaderRetryItem(
                    inspection,
                    mission_metadata,
                    storage_handler,
                    _retry_count=retry_count,
                )
                retry_item.increment_retry(self.max_wait_time)
                self.retry_queue.append(retry_item)
                self.logger.warning(
                    f"Storage handler: {type(storage_handler).__name__} "
                    f"failed to upload inspection: {str(inspection.id)[:8]}. "
                    f"Retrying in {retry_item.seconds_until_retry()}s."
                )
            else:
                self.logger.error(
                    f"Storage handler: {type(storage_handler).__name__} "
                    f"exceeded max retries to upload inspection: {str(inspection.id)[:8]}. Aborting upload."
                )

    def _process_retry_queue(self):
        ready_items: List[UploaderRetryItem] = [
            x for x in self.retry_queue if x.retry_is_ready()
        ]
        self.retry_queue = [x for x in self.retry_queue if not x.retry_is_ready()]
        for ready in ready_items:
            self._upload(
                ready.storage_handler,
                ready.inspection,
                ready.mission_metadata,
                ready.get_retry_count(),
            )
