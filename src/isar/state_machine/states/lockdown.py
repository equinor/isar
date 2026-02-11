from typing import TYPE_CHECKING, List, Union

import isar.state_machine.states.home as Home
import isar.state_machine.states.recharging as Recharging
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.services.service_connections.persistent_memory import (
    RobotStartupMode,
    change_persistent_robot_state,
    read_persistent_robot_state,
)
from isar.state_machine.states_enum import States

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Lockdown(State):

    def __init__(self, state_machine: "StateMachine"):
        events = state_machine.events

        def _release_from_lockdown_handler(
            should_release_from_lockdown: EmptyMessage,
        ) -> Union[Transition[Home.Home], Transition[Recharging.Recharging]]:
            events.api_requests.release_from_lockdown.response.trigger_event(
                EmptyMessage()
            )
            if state_machine.battery_level_is_above_mission_start_threshold():
                return Home.transition()
            else:
                return Recharging.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="release_from_lockdown",
                event=events.api_requests.release_from_lockdown.request,
                handler=_release_from_lockdown_handler,
            ),
        ]

        super().__init__(
            state_name=States.Lockdown,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[Lockdown]:
    def _transition(state_machine: "StateMachine") -> Lockdown:
        if settings.USE_DB:
            current_startup_mode = read_persistent_robot_state(settings.ISAR_ID)
            if current_startup_mode != RobotStartupMode.Lockdown:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Lockdown,
                )
        return Lockdown(state_machine)

    return _transition
