from queue import Queue

from isar.config.settings import settings
from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.status_queue import StatusQueue


class Events:
    def __init__(self) -> None:
        self.api_requests: APIRequests = APIRequests()
        self.state_machine_events: StateMachineEvents = StateMachineEvents()
        self.robot_service_events: RobotServiceEvents = RobotServiceEvents()

        self.upload_queue: Queue = Queue(maxsize=10)

        if settings.MQTT_ENABLED:
            self.mqtt_queue: Queue = Queue()


class APIRequests:
    def __init__(self) -> None:
        self.api_start_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.api_stop_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.api_pause_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.api_resume_mission: QueueIO = QueueIO(input_size=1, output_size=1)


class StateMachineEvents:
    def __init__(self) -> None:
        self.state_machine_start_mission: Queue = Queue(maxsize=1)
        self.state_machine_stop_mission: Queue = Queue(maxsize=1)
        self.state_machine_pause_mission: Queue = Queue(maxsize=1)
        self.state_machine_task_status_request: Queue = Queue(maxsize=1)
        self.state_machine_robot_status_request: Queue = Queue(maxsize=1)


class RobotServiceEvents:
    def __init__(self) -> None:
        self.robot_task_status: Queue = Queue(maxsize=1)
        self.robot_task_status_failed: Queue = Queue(maxsize=1)
        self.robot_mission_started: Queue = Queue(maxsize=1)
        self.robot_mission_failed: Queue = Queue(maxsize=1)
        self.robot_status_changed: Queue = Queue(maxsize=1)


class SharedState:
    def __init__(self) -> None:
        self.state: StatusQueue = StatusQueue()
        self.robot_status: StatusQueue = StatusQueue()
        self.state_machine_current_task: StatusQueue = StatusQueue()
