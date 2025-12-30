from collections import deque
from queue import Empty, Queue
from threading import Lock
from typing import Generic, Optional, Tuple, TypeVar

from isar.apis.models.models import (
    ControlMissionResponse,
    LockdownResponse,
    MaintenanceResponse,
    MissionStartResponse,
)
from isar.config.settings import settings
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus
from robot_interface.models.mission.task import TASKS

T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")


class Event(Queue[T]):
    def __init__(self, name: str) -> None:
        super().__init__(maxsize=1)
        self.name = name

    def trigger_event(self, data: T, timeout: int = None) -> None:
        try:
            # We always want a timeout when blocking for results, so that
            # the thread will never get stuck waiting for a result
            self.put(data, block=timeout is not None, timeout=timeout)
        except Exception:
            if timeout is not None:
                raise EventTimeoutError
            return None

    def consume_event(self, timeout: int = None) -> Optional[T]:
        try:
            return self.get(block=timeout is not None, timeout=timeout)
        except Empty:
            if timeout is not None:
                raise EventTimeoutError
            return None
        except ValueError:
            raise EventConflictError

    def clear_event(self) -> None:
        while True:
            try:
                self.get(block=False)
            except Empty:
                break
            except ValueError:
                break

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


class APIEvent(Generic[T1, T2]):
    """
    Creates request and response event. The events are defined such that the request is from
    api to state machine while the response is from state machine to api.
    """

    def __init__(self, name: str):
        self.request: Event[T1] = Event("api-" + name + "-request")
        self.response: Event[T2] = Event("api-" + name + "-request")
        self.lock: Lock = Lock()


class APIRequests:
    def __init__(self) -> None:
        self.start_mission: APIEvent[Mission, MissionStartResponse] = APIEvent(
            "start_mission"
        )
        self.stop_mission: APIEvent[str, ControlMissionResponse] = APIEvent(
            "stop_mission"
        )
        self.pause_mission: APIEvent[bool, ControlMissionResponse] = APIEvent(
            "pause_mission"
        )
        self.resume_mission: APIEvent[bool, ControlMissionResponse] = APIEvent(
            "resume_mission"
        )
        self.return_home: APIEvent[bool, bool] = APIEvent("return_home")
        self.release_intervention_needed: APIEvent[bool, bool] = APIEvent(
            "release_intervention_needed"
        )
        self.send_to_lockdown: APIEvent[bool, LockdownResponse] = APIEvent(
            "send_to_lockdown"
        )
        self.release_from_lockdown: APIEvent[bool, bool] = APIEvent(
            "release_from_lockdown"
        )
        self.set_maintenance_mode: APIEvent[bool, MaintenanceResponse] = APIEvent(
            "set_maintenance_mode"
        )
        self.release_from_maintenance_mode: APIEvent[bool, bool] = APIEvent(
            "release_from_maintenance_mode"
        )


class StateMachineEvents:
    def __init__(self) -> None:
        self.start_mission: Event[Mission] = Event("start_mission")
        self.stop_mission: Event[bool] = Event("stop_mission")
        self.pause_mission: Event[bool] = Event("pause_mission")
        self.resume_mission: Event[bool] = Event("resume_mission")


class RobotServiceEvents:
    def __init__(self) -> None:
        self.mission_status_updated: Event[MissionStatus] = Event(
            "mission_status_updated"
        )
        self.mission_started: Event[bool] = Event("mission_started")
        self.mission_failed: Event[ErrorMessage] = Event("mission_failed")
        self.robot_status_changed: Event[bool] = Event("robot_status_changed")
        self.mission_failed_to_stop: Event[ErrorMessage] = Event(
            "mission_failed_to_stop"
        )
        self.mission_successfully_stopped: Event[bool] = Event(
            "mission_successfully_stopped"
        )
        self.mission_failed_to_pause: Event[ErrorMessage] = Event(
            "mission_failed_to_pause"
        )
        self.mission_successfully_paused: Event[bool] = Event(
            "mission_successfully_paused"
        )
        self.mission_failed_to_resume: Event[ErrorMessage] = Event(
            "mission_failed_to_resume"
        )
        self.mission_successfully_resumed: Event[bool] = Event(
            "mission_successfully_resumed"
        )
        self.request_inspection_upload: Event[Tuple[TASKS, Mission]] = Event(
            "request_inspection_upload"
        )
        self.robot_already_home: Event[bool] = Event("robot_already_home")


class SharedState:
    def __init__(self) -> None:
        self.state: Event[States] = Event("state")
        self.robot_status: Event[RobotStatus] = Event("robot_status")
        self.robot_battery_level: Event[float] = Event("robot_battery_level")


class EventTimeoutError(Exception):
    pass


class EventConflictError(Exception):
    pass
