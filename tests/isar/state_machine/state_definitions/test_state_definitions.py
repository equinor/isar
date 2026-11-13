"""Structural checks over every state definition, without running any handlers."""

from dataclasses import fields

from isar.models.events import Events
from isar.state_machine.state import Branch, TimeoutHandler, TransitionDef
from isar.state_machine.states import STATE_MODULES
from isar.state_machine.states_enum import States

_ALWAYS = next(f.default for f in fields(Branch) if f.name == "transition_when")


def test_every_state_is_registered_exactly_once() -> None:
    names = [module.state.name for module in STATE_MODULES]
    assert sorted(names) == sorted(States)


def test_transition_definitions_belong_to_the_module_they_are_defined_in() -> None:
    for module in STATE_MODULES:
        for attribute, value in vars(module).items():
            if isinstance(value, TransitionDef):
                assert (
                    value.state_definition is module.state
                ), f"{module.__name__}.{attribute} enters another state"


def test_no_state_handles_the_same_event_twice() -> None:
    events = Events()
    for module in STATE_MODULES:
        handled = [id(handler.event(events)) for handler in module.state.handlers()]
        assert len(handled) == len(set(handled)), module.state.name


def test_every_handler_has_reachable_branches() -> None:
    for module in STATE_MODULES:
        handlers = [*module.state.handlers(), *module.state.timers()]
        for handler in handlers:
            assert (
                handler.branches
            ), f"{module.state.name} has a handler with no branches"
            unconditional = [b.transition_when is _ALWAYS for b in handler.branches]
            assert (
                True not in unconditional[:-1]
            ), f"{module.state.name} has a branch after an unconditional branch"
            if isinstance(handler, TimeoutHandler):
                assert (
                    handler.timeout_in_seconds >= 0
                ), f"{handler.name} in {module.state.name} has a negative timeout"
