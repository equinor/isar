from queue import Queue

from transitions import State

from isar.config.settings import settings
from isar.models.communication.queues.queue_io import QueueIO
from isar.models.communication.queues.status_queue import StatusQueue
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import TASKS


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
        self.start_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.stop_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.pause_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.resume_mission: QueueIO = QueueIO(input_size=1, output_size=1)
        self.return_home: QueueIO = QueueIO(input_size=1, output_size=1)


class StateMachineEvents:
    def __init__(self) -> None:
        self.start_mission: Queue[Mission] = Queue(maxsize=1)
        self.stop_mission: Queue[bool] = Queue(maxsize=1)
        self.pause_mission: Queue[bool] = Queue(maxsize=1)
        self.task_status_request: Queue[str] = Queue(maxsize=1)


class RobotServiceEvents:
    def __init__(self) -> None:
        self.task_status_updated: Queue[TaskStatus] = Queue(maxsize=1)
        self.task_status_failed: Queue[ErrorMessage] = Queue(maxsize=1)
        self.mission_started: Queue[bool] = Queue(maxsize=1)
        self.mission_failed: Queue[ErrorMessage] = Queue(maxsize=1)
        self.robot_status_changed: Queue[bool] = Queue(maxsize=1)
        self.mission_failed_to_stop: Queue[ErrorMessage] = Queue(maxsize=1)
        self.mission_successfully_stopped: Queue[bool] = Queue(maxsize=1)


class SharedState:
    def __init__(self) -> None:
        self.state: StatusQueue[State] = StatusQueue()
        self.robot_status: StatusQueue[RobotStatus] = StatusQueue()
        self.state_machine_current_task: StatusQueue[TASKS] = StatusQueue()
