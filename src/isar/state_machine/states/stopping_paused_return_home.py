import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import MissionStartResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


def StoppingPausedReturnHome(events: Events, mission: Mission) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: InterventionNeeded.transition(
                "Failed to stop paused return home mission"
            ),
        ),
        EventHandlerMapping[AbortedMission | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=lambda _: Monitor.transition_and_start_mission(mission, True),
        ),
    ]
    return State(
        state_name=States.StoppingPausedReturnHome,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_stop_return_home_and_reply_to_API(
    mission: Mission,
) -> Transition:
    def _transition(events: Events) -> State:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())

        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        events.api_requests.start_mission.response.trigger_event(response)

        return StoppingPausedReturnHome(events, mission)

    return _transition
