import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping as Stopping
from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import (
    EventHandlerMapping,
    State,
    TimeoutHandlerMapping,
    Transition,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


class AwaitNextMission(State):

    def __init__(self, events: Events):

        event_handlers: list[EventHandlerMapping] = [
            EventHandlerMapping[Mission](
                event=events.api_requests.start_mission.request,
                handler=lambda mission: Monitor.transition_and_start_mission(
                    mission, True
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.return_home.request,
                handler=lambda _: ReturningHome.transition_and_start_mission(True),
            ),
            EventHandlerMapping[str](
                event=events.api_requests.stop_mission.request,
                handler=lambda mission_id: Stopping.transition_and_trigger_stop_and_respond_to_API(
                    mission_id
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: GoingToLockdown.transition_and_start_mission_and_report_to_api(),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: GoingToRecharging.transition_and_start_return_home(),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
        ]

        timers: list[TimeoutHandlerMapping] = [
            TimeoutHandlerMapping(
                name="should_return_home_timer",
                timeout_in_seconds=settings.RETURN_HOME_DELAY,
                handler=lambda: ReturningHome.transition_and_start_mission(),
            )
        ]

        super().__init__(
            state_name=States.AwaitNextMission,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
            timers=timers,
        )


def transition() -> Transition[AwaitNextMission]:
    def _transition(events: Events) -> AwaitNextMission:
        return AwaitNextMission(events)

    return _transition
