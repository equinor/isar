import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.return_home_paused as ReturnHomePaused
from isar.apis.models.models import MissionStartResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


def StoppingPausedReturnHome(events: Events, mission: Mission) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_failed_to_stop,
            handler=lambda _: ReturnHomePaused.transition(),
        ),
        EventHandlerMapping[AbortedMission](
            event=events.robot_service_events.mission_successfully_stopped,
            handler=lambda _: Monitor.transition_and_start_mission(mission, True),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.stopped_mission_already_done,
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
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())

        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        events.api_requests.start_mission.response.trigger_event(response)

        return StoppingPausedReturnHome(events, mission)

    return _transition
