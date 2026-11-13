"""Behaviour of the framework itself, tested once with minimal ad-hoc states."""

from isar.models.events import EmptyMessage
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TimeoutHandler,
    TransitionDef,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus
from tests.isar.state_machine.state_definitions.state_machine_driver import (
    StateMachineDriver,
    state_machine_driver,
)

__all__ = ["state_machine_driver"]

_target: StateDef[str] = StateDef(name=States.Paused, handlers=lambda: ())


def _source(calls: list[str]) -> StateDef[int]:
    to_target: TransitionDef[int, str] = TransitionDef(
        _target,
        lambda value: f"param-{value}",
        side_effect=lambda _, value: calls.append(f"transition {value}"),
    )
    return StateDef(
        name=States.Monitor,
        handlers=lambda: (
            EventHandler(
                event=lambda e: e.robot_async_events.robot_status_update,
                branches=(
                    Branch(
                        to_target,
                        lambda param, _: param + 1,
                        transition_when=lambda _, status: status == RobotStatus.Busy,
                        side_effect=lambda _, param, status: calls.append(
                            f"handler {param} {status.name}"
                        ),
                    ),
                    Branch(
                        to_target,
                        lambda param, _: param + 100,
                        transition_when=lambda _, status: status == RobotStatus.Busy,
                    ),
                ),
            ),
        ),
    )


def test_starts_in_unknown_status(state_machine_driver: StateMachineDriver) -> None:
    assert state_machine_driver.state.name is States.UnknownStatus


def test_first_matching_branch_is_taken_and_side_effects_run_in_order(
    state_machine_driver: StateMachineDriver,
) -> None:
    calls: list[str] = []
    state_machine_driver.enter(_source(calls), 1)

    new_state = state_machine_driver.send(
        state_machine_driver.events.robot_async_events.robot_status_update,
        RobotStatus.Busy,
    )

    assert new_state is States.Paused
    assert state_machine_driver.state.param == "param-2"
    assert calls == ["handler 1 Busy", "transition 2"]


def test_event_matching_no_branch_is_consumed_and_ignored(
    state_machine_driver: StateMachineDriver,
) -> None:
    calls: list[str] = []
    state_machine_driver.enter(_source(calls), 1)

    new_state = state_machine_driver.send(
        state_machine_driver.events.robot_async_events.robot_status_update,
        RobotStatus.Available,
    )

    assert new_state is States.Monitor
    assert calls == []
    assert (
        not state_machine_driver.events.robot_async_events.robot_status_update.has_event()
    )


def test_events_not_handled_by_the_state_are_left_in_their_queue(
    state_machine_driver: StateMachineDriver,
) -> None:
    state_machine_driver.enter(_source([]), 1)
    battery_low = (
        state_machine_driver.events.robot_async_events.battery_below_mission_threshold
    )

    new_state = state_machine_driver.send(battery_low, EmptyMessage())

    assert new_state is States.Monitor
    assert not state_machine_driver.state.handles_event(battery_low)
    assert battery_low.has_event()


def test_timeout_handler_triggers_its_branch_only_after_timeout(
    state_machine_driver: StateMachineDriver,
) -> None:
    to_target: TransitionDef[None, str] = TransitionDef(_target, lambda _: "")
    state_machine_driver.enter(
        StateDef[None](
            name=States.Monitor,
            handlers=lambda: (),
            timers=lambda: (
                TimeoutHandler(
                    name="timer", timeout_in_seconds=5, branches=(Branch(to_target),)
                ),
            ),
        )
    )

    assert state_machine_driver.step(elapsed_seconds=5) is States.Monitor
    assert state_machine_driver.step(elapsed_seconds=6) is States.Paused


def test_exit_signal_stops_the_state_without_transitioning(
    state_machine_driver: StateMachineDriver,
) -> None:
    state_machine_driver.machine.signal_exit.trigger_event(EmptyMessage())

    assert state_machine_driver.state.run() is None
