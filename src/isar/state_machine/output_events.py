from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from isar.models.events import (
    APIEvent,
    APIRequests,
    Events,
    RobotActionEvent,
    RobotActionRequests,
)
from isar.models.mqtt_queue import MQTTQueue


@dataclass(frozen=True)
class OutputEvent[T]:
    select: Callable[[Events], Callable[[T], None]]

    def __call__(self, events: Events) -> Callable[[T], None]:
        return self.select(events)

    @staticmethod
    def api_response[T1](
        select: Callable[[APIRequests], APIEvent[Any, T1]],
    ) -> OutputEvent[T1]:
        return OutputEvent(lambda e: select(e.api_requests).trigger_response)

    @staticmethod
    def robot_request[T1](
        select: Callable[[RobotActionRequests], RobotActionEvent[T1, Any, Any]],
    ) -> OutputEvent[T1]:
        return OutputEvent(lambda e: select(e.action_requests).trigger_request)

    @staticmethod
    def mqtt[T1](
        select: Callable[[MQTTQueue], Callable[[T1], None]],
    ) -> OutputEvent[T1]:
        return OutputEvent(lambda e: select(e.mqtt_queue))

    @staticmethod
    def clear_robot_status() -> OutputEvent[None]:
        def clear(events: Events) -> Callable[[None], None]:
            def run(_: None) -> None:
                events.robot_async_events.robot_status_update.clear_event()

            return run

        return OutputEvent(clear)
