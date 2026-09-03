import isar.state_machine.states.resuming as Resuming
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
import isar.state_machine.states.stopping_paused_mission as StoppingPausedMission
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def Paused(events: Events, mission_id: str) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.stop_mission.request,
            handler=lambda _: StoppingPausedMission.transition_and_trigger_stop(
                mission_id, True
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.resume_mission.request,
            handler=lambda _: Resuming.transition_resume_mission_and_respond_to_API(
                mission_id
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_async_events.battery_below_mission_threshold,
            handler=lambda _: StoppingGoToRecharge.transition_and_stop_mission(),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.send_to_lockdown.request,
            handler=lambda _: StoppingGoToLockdown.transition_and_stop_mission(
                mission_id
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(
                mission_id
            ),
        ),
    ]
    return State(
        state_name=States.Paused,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition(mission_id: str) -> Transition:
    def _transition(events: Events) -> State:
        return Paused(events, mission_id)

    return _transition
