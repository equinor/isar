from typing import TYPE_CHECKING, List

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.models.events import Event
from robot_interface.models.mission.status import RobotStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Recharging(EventHandlerBase):

    def __init__(self, state_machine: "StateMachine"):
        shared_state = state_machine.shared_state

        def robot_battery_level_updated_handler(event: Event[float]):
            battery_level: float = event.check()
            if battery_level >= settings.ROBOT_BATTERY_RECHARGE_THRESHOLD:
                return state_machine.robot_recharged  # type: ignore
            return None

        def robot_offline_handler(event: Event[RobotStatus]):
            robot_status: RobotStatus = event.check()
            if robot_status == RobotStatus.Offline:
                return state_machine.robot_went_offline  # type: ignore

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=robot_battery_level_updated_handler,
            ),
            EventHandlerMapping(
                name="robot_offline_event",
                event=shared_state.robot_status,
                handler=robot_offline_handler,
            ),
        ]
        super().__init__(
            state_name="recharging",
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )
