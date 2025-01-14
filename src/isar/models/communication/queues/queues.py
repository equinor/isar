from queue import Queue

from isar.config.settings import settings
from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.status_queue import StatusQueue


class Queues:
    def __init__(self) -> None:
        self.api_start_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.api_stop_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.api_pause_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.api_resume_mission: QueueIO = QueueIO(input_size=1, output_size=1)

        self.state_machine_start_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.state_machine_stop_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.state_machine_pause_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.state_machine_current_task: StatusQueue = StatusQueue()

        self.robot_offline: QueueIO = QueueIO(input_size=1, output_size=1)
        self.robot_online: QueueIO = QueueIO(input_size=1, output_size=1)
        self.robot_task_status: QueueIO = QueueIO(input_size=1, output_size=1)
        self.robot_task_status_failed: QueueIO = QueueIO(input_size=1, output_size=1)
        self.robot_mission_started: QueueIO = QueueIO(input_size=1, output_size=1)
        self.robot_mission_failed: QueueIO = QueueIO(input_size=1, output_size=1)

        self.upload_queue: Queue = Queue(maxsize=10)
        self.state: StatusQueue = StatusQueue()

        if settings.MQTT_ENABLED:
            self.mqtt_queue: Queue = Queue()
