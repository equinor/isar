from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


def test_transition_from_pausing_return_home_to_return_home_paused(
    events: Events,
) -> None:
    current_state = PausingReturnHome(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.action_requests.pause_mission.success
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.ReturnHomePaused


def test_resuming_paused_return_home(events: Events) -> None:
    current_state = ReturnHomePaused(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.resume_mission.request
    )

    transition = event_handler.handler(EmptyMessage())

    current_state = transition(events)
    assert current_state.name is States.ResumingReturnHome


def test_transition_from_paused_return_home_to_stopping_paused_return_home_mission(
    events: Events,
) -> None:
    current_state = ReturnHomePaused(events)

    event_handler: EventHandlerMapping = current_state.get_event_handler_by_event(
        events.api_requests.start_mission.request
    )

    example_mission: Mission = Mission(id="id", name="Dummy misson", tasks=[])

    transition = event_handler.handler(example_mission)

    current_state = transition(events)

    assert events.api_requests.start_mission.response.has_event()
    assert current_state.name is States.StoppingPausedReturnHome
