from collections import deque
from queue import Empty, Queue
from typing import Optional, TypeVar

from transitions import State

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import TASKS

T = TypeVar("T")


class Event(Queue[T]):
    def __init__(self) -> None:
        super().__init__(maxsize=1)

    def trigger_event(self, data: T) -> None:
        self.put(data)

    def consume_event(self) -> Optional[T]:
        try:
            return self.get(block=False)
        except Empty:
            return None

    def has_event(self) -> bool:
        return (
            self.qsize() != 0
        )  # Queue size is not reliable, but should be sufficient for this case

    def check(self) -> Optional[T]:
        if not self._qsize():
            return None
        with self.mutex:
            queueList = list(self.queue)
            return queueList.pop()

    def update(self, item: T):
        with self.mutex:
            self.queue: deque[T] = deque()
            self.queue.append(item)


class Events:
    def __init__(self) -> None:
        self.api_requests: APIRequests = APIRequests()
        self.state_machine_events: StateMachineEvents = StateMachineEvents()
        self.robot_service_events: RobotServiceEvents = RobotServiceEvents()

        self.upload_queue: Queue = Queue(maxsize=10)

        if settings.MQTT_ENABLED:
            self.mqtt_queue: Queue = Queue()


class APIEvent:
    """
    Creates input and output event. The events are defined such that the input is from
    api to state machine while the output is from state machine to api.
    """

    def __init__(self):
        self.input: Event = Event()
        self.output: Event = Event()


class APIRequests:
    def __init__(self) -> None:
        self.start_mission: APIEvent = APIEvent()
        self.stop_mission: APIEvent = APIEvent()
        self.pause_mission: APIEvent = APIEvent()
        self.resume_mission: APIEvent = APIEvent()
        self.return_home: APIEvent = APIEvent()


class StateMachineEvents:
    def __init__(self) -> None:
        self.start_mission: Event[Mission] = Event()
        self.stop_mission: Event[bool] = Event()
        self.pause_mission: Event[bool] = Event()
        self.task_status_request: Event[str] = Event()


class RobotServiceEvents:
    def __init__(self) -> None:
        self.task_status_updated: Event[TaskStatus] = Event()
        self.task_status_failed: Event[ErrorMessage] = Event()
        self.mission_started: Event[bool] = Event()
        self.mission_failed: Event[ErrorMessage] = Event()
        self.robot_status_changed: Event[bool] = Event()
        self.mission_failed_to_stop: Event[ErrorMessage] = Event()
        self.mission_successfully_stopped: Event[bool] = Event()


class SharedState:
    def __init__(self) -> None:
        self.state: Event[State] = Event()
        self.robot_status: Event[RobotStatus] = Event()
        self.state_machine_current_task: Event[TASKS] = Event()
