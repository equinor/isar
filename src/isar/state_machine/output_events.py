from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from isar.models.events import (
    APIEvent,
    APIRequests,
    RobotActionEvent,
    RobotActionRequests,
    RobotAsyncEvents,
)
from isar.models.mqtt_queue import MQTTQueue


class ApiResponder:
    def __init__(self, api_requests: APIRequests) -> None:
        self._api_requests = api_requests

    def respond[T](
        self, select: Callable[[APIRequests], APIEvent[Any, T]], value: T
    ) -> None:
        select(self._api_requests).trigger_response(value)


class RobotCommander:
    def __init__(
        self,
        action_requests: RobotActionRequests,
        robot_async_events: RobotAsyncEvents,
    ) -> None:
        self._action_requests = action_requests
        self._robot_async_events = robot_async_events

    def request[T](
        self,
        select: Callable[[RobotActionRequests], RobotActionEvent[T, Any, Any]],
        value: T,
    ) -> None:
        select(self._action_requests).trigger_request(value)

    def clear_robot_status(self) -> None:
        self._robot_async_events.robot_status_update.clear_event()


@dataclass(frozen=True)
class OutputEvents:
    """Available to the side effects of branches and transitions."""

    api: ApiResponder
    robot: RobotCommander
    mqtt: MQTTQueue
