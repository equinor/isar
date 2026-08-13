import isar.state_machine.states.return_home_paused as ReturnHomePaused
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def PausingReturnHome(events: Events) -> State:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_failed_to_pause,
            handler=lambda _: ReturningHome.transition_to_existing_mission(),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_successfully_paused,
            handler=lambda _: ReturnHomePaused.transition(),
        ),
    ]
    return State(
        state_name=States.PausingReturnHome,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_pause_mission_and_reply_to_API() -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.pause_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        events.state_machine_events.pause_mission.trigger_event(EmptyMessage())
        return PausingReturnHome(events)

    return _transition
