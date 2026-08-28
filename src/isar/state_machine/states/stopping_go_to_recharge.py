import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.going_to_recharging_with_mission as GoingToRechargingWithMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def StoppingGoToRecharge(events: Events) -> State:

    def _mission_stopped_event_handler(
        aborted_mission: AbortedMission | EmptyMessage,
    ) -> Transition:
        if isinstance(aborted_mission, AbortedMission):
            return GoingToRechargingWithMission.transition_and_start_return_home(
                aborted_mission
            )
        else:
            return GoingToRecharging.transition_and_start_return_home()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                "Failed to stop mission when battery was low"
            ),
        ),
        EventHandlerMapping[AbortedMission | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=_mission_stopped_event_handler,
        ),
    ]
    return State(
        state_name=States.StoppingGoToRecharge,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_stop_mission() -> Transition:
    def _transition(events: Events) -> State:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        return StoppingGoToRecharge(events)

    return _transition
