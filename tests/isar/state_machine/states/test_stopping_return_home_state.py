from typing import Optional, cast

from isar.eventhandlers.eventhandler import EventHandlerMapping, State
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from tests.test_mocks.task import StubTask


def test_return_home_cancelled_when_new_mission_received(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(80.0)
    sync_state_machine.current_state = ReturningHome(sync_state_machine)

    returning_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("start_mission_event")
    )

    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])

    assert event_handler is not None

    transition = event_handler.handler(mission)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is StoppingReturnHome


def test_stopping_return_home_mission_fails(
    sync_state_machine: StateMachine,
) -> None:
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    sync_state_machine.current_state = StoppingReturnHome(sync_state_machine, mission)
    stopping_return_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_return_home_state.get_event_handler_by_name("failed_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(
        ErrorMessage(error_description="", error_reason=ErrorReason.RobotAPIException)
    )

    assert sync_state_machine.events.api_requests.start_mission.response.has_event()

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is ReturningHome


def test_stopping_return_home_mission_succeeds(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(90.0)
    mission: Mission = Mission(name="Dummy misson", tasks=[StubTask.take_image()])
    sync_state_machine.current_state = StoppingReturnHome(sync_state_machine, mission)
    stopping_return_home_state: State = cast(State, sync_state_machine.current_state)
    event_handler: Optional[EventHandlerMapping] = (
        stopping_return_home_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    transition = event_handler.handler(True)

    sync_state_machine.current_state = transition(sync_state_machine)
    assert type(sync_state_machine.current_state) is Monitor
