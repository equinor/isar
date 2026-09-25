import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.going_to_recharging_with_mission as GoingToRechargingWithMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.models.events import AbortedMission, EmptyMessage, Events, MissionCompleted
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def StoppingGoToRecharge(events: Events, mission_id: str | None = None) -> State:

    def _mission_stopped_event_handler(
        stop_result: AbortedMission | MissionCompleted | EmptyMessage,
    ) -> Transition:
        if isinstance(stop_result, AbortedMission):
            return GoingToRechargingWithMission.transition_and_start_return_home(
                stop_result
            )
        if isinstance(stop_result, MissionCompleted) and mission_id:
            events.mqtt_queue.publish_mission_aborted(
                mission_id,
                "Mission aborted because the robot began recharging after all tasks completed",
            )
        return GoingToRecharging.transition_and_start_return_home()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                "Failed to stop mission when battery was low"
            ),
        ),
        EventHandlerMapping[AbortedMission | MissionCompleted | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=_mission_stopped_event_handler,
        ),
    ]
    return State(
        state_name=States.StoppingGoToRecharge,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_stop_mission(mission_id: str | None = None) -> Transition:
    def _transition(events: Events) -> State:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        return StoppingGoToRecharge(events, mission_id)

    return _transition
