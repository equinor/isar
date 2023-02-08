from queue import Queue

from isar.config.settings import settings
from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.status_queue import StatusQueue


class Queues:
    def __init__(self) -> None:
        self.start_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.stop_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.pause_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.resume_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.single_action: QueueIO = QueueIO(input_size=1, output_size=1)
        self.upload_queue: Queue = Queue(maxsize=10)
        self.state: StatusQueue = StatusQueue()

        if settings.MQTT_ENABLED:
            self.mqtt_queue: Queue = Queue()
