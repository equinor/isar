import logging
from queue import Empty, Queue
from typing import Any

from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError

logger = logging.getLogger("api")


class QueueUtilities:
    """
    Contains utility functions for handling queue communication between threads.
    """

    @staticmethod
    def check_queue(queue: Queue, queue_timeout: int = None) -> Any:
        """
        Checks if there is a message on a queue. If a timeout is specified the function
        will raise a QueueTimeoutError if there is no message within the timeout. If
        there is no timeout specified this function will block.
        :param queue: The queue to be checked for a message
        :param queue_timeout: Timeout in seconds
        :return: Message found on queue
        :raises QueueTimeoutError
        """
        try:
            message: Any = queue.get(timeout=queue_timeout)
        except Empty:
            logger.error("Queue timed out")
            raise QueueTimeoutError
        return message

    @staticmethod
    def clear_queue(queue: Queue) -> None:
        while True:
            try:
                queue.get(block=False)
            except Empty:
                break
