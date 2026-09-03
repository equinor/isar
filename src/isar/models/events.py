from collections import deque
from queue import Empty, Full, Queue, ShutDown

from isar.apis.models.models import (
    ControlMissionResponse,
    LockdownResponse,
    MaintenanceResponse,
    MissionStartResponse,
)
from isar.models.mqtt_queue import MQTTQueue
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.event_exceptions import (
    EventConflictError,
    EventTimeoutError,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus
from robot_interface.models.mission.task import InspectionTask


class EmptyMessage:
    def __str__(self) -> str:
        return "Empty message"


AbortedMission = Mission


class Event[T](Queue[T]):
    def __init__(self, name: str, maxsize: int = 1) -> None:
        super().__init__(maxsize=maxsize)
        self.name = name

    def trigger_event(self, data: T, timeout: int | None = None) -> None:
        try:
            # We always want a timeout when blocking for results, so that
            # the thread will never get stuck waiting for a result
            self.put(data, block=timeout is not None, timeout=timeout)
        except Full, ShutDown, ValueError:
            if timeout is not None:
                raise EventTimeoutError
            return

    def consume_event(self, timeout: int | None = None) -> T | None:
        try:
            return self.get(block=timeout is not None, timeout=timeout)
        except Empty:
            if timeout is not None:
                raise EventTimeoutError
            return None
        except ValueError, ShutDown:
            raise EventConflictError

    def clear_event(self) -> bool:
        while True:
            try:
                self.get(block=False)
                return True
            except Empty:
                return False
            except ValueError:
                return False

    def has_event(self) -> bool:
        return (
            self.qsize() != 0
        )  # Queue size is not reliable, but should be sufficient for this case

    def check(self) -> T | None:
        if not self._qsize():
            return None
        with self.mutex:
            queueList = list(self.queue)
            return queueList.pop()

    def update(self, item: T) -> None:
        with self.mutex:
            self.queue: deque[T] = deque()
            self.queue.append(item)


class Events:
    def __init__(self) -> None:
        self.signal_state_machine_exit: Event[EmptyMessage] = Event(
            "signal_state_machine_exit"
        )

        self.api_requests: APIRequests = APIRequests()
        self.action_requests: RobotActionRequests = RobotActionRequests()
        self.robot_async_events: RobotAsyncEvents = RobotAsyncEvents()

        self.upload_event: Event[tuple[Inspection, Mission]] = Event(
            "uploader", maxsize=10
        )

        self.mqtt_queue: MQTTQueue = MQTTQueue(maxsize=30)

        self.state: Event[States] = Event("state")


class APIEvent[T1, T2]:
    """
    Creates request and response event. The events are defined such that the request is from
    api to state machine while the response is from state machine to api.
    """

    prioritized: bool

    def __init__(self, name: str, prioritized: bool = False):
        self.request: Event[T1] = Event("api-" + name + "-request")
        self.response: Event[T2] = Event("api-" + name + "-response")
        self.prioritized = (
            prioritized  # For when we want to try even if the statemachine is not ready
        )


class APIRequests:
    def __init__(self) -> None:
        self.start_mission: APIEvent[Mission, MissionStartResponse] = APIEvent(
            "start_mission"
        )
        self.stop_mission: APIEvent[EmptyMessage, ControlMissionResponse] = APIEvent(
            "stop_mission"
        )
        self.pause_mission: APIEvent[EmptyMessage, ControlMissionResponse] = APIEvent(
            "pause_mission"
        )
        self.resume_mission: APIEvent[EmptyMessage, ControlMissionResponse] = APIEvent(
            "resume_mission"
        )
        self.return_home: APIEvent[EmptyMessage, EmptyMessage] = APIEvent("return_home")
        self.release_intervention_needed: APIEvent[EmptyMessage, EmptyMessage] = (
            APIEvent("release_intervention_needed")
        )
        self.send_to_lockdown: APIEvent[EmptyMessage, LockdownResponse] = APIEvent(
            "send_to_lockdown", prioritized=True
        )
        self.release_from_lockdown: APIEvent[EmptyMessage, EmptyMessage] = APIEvent(
            "release_from_lockdown"
        )
        self.set_maintenance_mode: APIEvent[EmptyMessage, MaintenanceResponse] = (
            APIEvent("set_maintenance_mode", prioritized=True)
        )
        self.release_from_maintenance_mode: APIEvent[EmptyMessage, EmptyMessage] = (
            APIEvent("release_from_maintenance_mode")
        )


class RobotActionEvent[T1, T2, T3]:
    """
    Creates request and response event. The events are defined such that the request is from
    state machine to robot service, and vice versa for the response. Only one response per
    request is expected, and other events are cleared before the next one is triggered.
    """

    def __init__(self, name: str) -> None:
        self.request: Event[T1] = Event("robot-" + name + "-request")
        self.success: Event[T2] = Event("robot-" + name + "-success")
        self.failure: Event[T3] = Event("robot-" + name + "-failure")

    def trigger_request(self, event_value: T1) -> None:
        self.failure.clear_event()
        self.success.clear_event()
        self.request.trigger_event(event_value)

    def trigger_success_response(self, event_value: T2) -> None:
        self.failure.clear_event()
        self.success.trigger_event(event_value)

    def trigger_failure_response(self, event_value: T3) -> None:
        self.success.clear_event()
        self.failure.trigger_event(event_value)


class RobotActionRequests:
    def __init__(self) -> None:
        self.execute_mission: RobotActionEvent[Mission, EmptyMessage, ErrorMessage] = (
            RobotActionEvent("execute_mission")
        )
        self.stop_mission: RobotActionEvent[
            EmptyMessage, AbortedMission | EmptyMessage, EmptyMessage
        ] = RobotActionEvent("stop_mission")
        self.pause_mission: RobotActionEvent[
            EmptyMessage, EmptyMessage, EmptyMessage
        ] = RobotActionEvent("pause_mission")
        self.resume_mission: RobotActionEvent[
            EmptyMessage, EmptyMessage, EmptyMessage
        ] = RobotActionEvent("resume_mission")


class RobotAsyncEvents:
    def __init__(self) -> None:
        self.robot_status_update: Event[RobotStatus] = Event("robot_status_update")
        self.request_inspection_upload: Event[tuple[InspectionTask, Mission]] = Event(
            "request_inspection_upload"
        )
        self.battery_below_mission_threshold: Event[EmptyMessage] = Event(
            "battery_below_mission_threshold"
        )
        self.battery_above_recharge_threshold: Event[EmptyMessage] = Event(
            "battery_above_recharge_threshold"
        )
