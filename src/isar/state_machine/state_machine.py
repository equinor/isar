import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.models.mqtt_queue import MQTTQueue
from isar.models.status import IsarStatus
from isar.services.service_connections.persistent_memory import (
    NoSuchRobotException,
    RobotStartupMode,
    change_persistent_robot_state,
    create_persistent_robot_state,
    read_persistent_robot_state,
)
from isar.state_machine.capabilities import ApiResponder, OutputEvents, RobotCommander
from isar.state_machine.state import (
    Branch,
    State,
    TimeoutHandler,
    Transition,
    TransitionDef,
)
from isar.state_machine.state_metrics import StateMetricsPublisher
from isar.state_machine.states import STATE_MODULES
from isar.state_machine.states import going_to_lockdown as GoingToLockdown
from isar.state_machine.states import maintenance as Maintenance
from isar.state_machine.states import unknown_status as UnknownStatus
from isar.state_machine.states_enum import States


class StateMachine:
    """Handles state transitions for supervisory robot control."""

    def __init__(self, events: Events, mqtt_queue: MQTTQueue) -> None:
        self.logger = logging.getLogger("state_machine")

        self.events: Events = events
        self.mqtt_queue: MQTTQueue = mqtt_queue

        self.signal_exit: Event[EmptyMessage] = Event("signal_state_machine_exit")

        self._output_events = OutputEvents(
            api=ApiResponder(events.api_requests),
            robot=RobotCommander(events.action_requests, events.robot_async_events),
            mqtt=mqtt_queue,
        )

        initial = Transition(UnknownStatus.transition, None)
        if not settings.USE_DB:
            self.logger.warning(
                "Not using ISAR database. Restarting ISAR will forget the state, including maintenance mode. "
            )
        else:
            robot_startup_mode = read_or_create_persistent_mode()
            self.logger.info(
                f"Connected to robot status database and the startup mode was: {robot_startup_mode}. "
            )
            if robot_startup_mode == RobotStartupMode.Maintenance:
                initial = Transition(Maintenance.transition, None)
            elif robot_startup_mode == RobotStartupMode.Lockdown:
                initial = Transition(
                    GoingToLockdown.transition_with_existing_mission, None
                )

        self.current_state: State = self._enter(initial)

        self.transitions_list: deque[States] = deque(
            [], settings.STATE_TRANSITIONS_LOG_LENGTH
        )

        self.state_metrics_publisher: StateMetricsPublisher = StateMetricsPublisher(
            current_state_provider=lambda: self.current_state.name
        )

    def _enter[A](self, transition: Transition[A]) -> State:
        entry = transition.transition_function
        if entry.side_effect is not None:
            entry.side_effect(self._output_events, transition.transition_input)
        return State(
            entry.state_definition,
            entry.state_param(transition.transition_input),
            self.events,
            self._output_events,
            self.signal_exit,
        )

    def current_state_handles_event(self, event: Event) -> bool:
        return self.current_state.handles_event(event)

    def run(self) -> None:
        """Runs the state machine loop."""
        try:
            while True:
                self.update_state(self.current_state)
                transition = self.current_state.run()

                if transition is None:  # Expected when the thread is killed
                    self.logger.warning(
                        "Exiting state machine as next transition is None"
                    )
                    break

                self.logger.debug(
                    f"Transitioning from {self.current_state.name.name} to {transition.transition_function.state_definition.name.name}"
                )
                self.current_state = self._enter(transition)
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Unhandled exception in state machine: {e!s}")

    def terminate(self) -> None:
        self.logger.info("Stopping state machine")
        self.signal_exit.trigger_event(EmptyMessage())

    def update_state(self, current_state: State) -> None:
        """Updates the current state of the state machine."""

        if settings.USE_DB:
            if current_state.name in [
                States.StoppingGoToLockdown,
                States.GoingToLockdown,
                States.GoingToLockdownWithMission,
                States.LockdownWithMission,
                States.Lockdown,
            ]:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Lockdown,
                )
            elif current_state.name == States.Maintenance:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Maintenance,
                )
            else:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Normal,
                )

        self.transitions_list.append(current_state.name)
        self.logger.info("State: %s", current_state.name)
        self.mqtt_queue.publish_isar_status(state_to_status(current_state.name))


def state_to_status(state_name: States) -> IsarStatus:
    if state_name == States.AwaitNextMission:
        return IsarStatus.Available
    elif state_name == States.ReturnHomePaused:
        return IsarStatus.ReturnHomePaused
    elif state_name == States.Paused:
        return IsarStatus.Paused
    elif state_name == States.Home:
        return IsarStatus.Home
    elif state_name == States.ReturningHome:
        return IsarStatus.ReturningHome
    elif state_name == States.Offline:
        return IsarStatus.Offline
    elif state_name == States.InterventionNeeded:
        return IsarStatus.InterventionNeeded
    elif state_name == States.Recharging:
        return IsarStatus.Recharging
    elif state_name == States.RechargingWithMission:
        return IsarStatus.RechargingWithMission
    elif state_name in [States.Lockdown, States.LockdownWithMission]:
        return IsarStatus.Lockdown
    elif state_name in [States.GoingToLockdown, States.GoingToLockdownWithMission]:
        return IsarStatus.GoingToLockdown
    elif state_name == States.GoingToRecharging:
        return IsarStatus.GoingToRecharging
    elif state_name == States.GoingToRechargingWithMission:
        return IsarStatus.GoingToRechargingWithMission
    elif state_name == States.Maintenance:
        return IsarStatus.Maintenance
    elif state_name == States.Pausing:
        return IsarStatus.Pausing
    elif state_name == States.PausingReturnHome:
        return IsarStatus.PausingReturnHome
    elif state_name in [
        States.Stopping,
        States.StoppingDueToMaintenance,
        States.StoppingGoToLockdown,
        States.StoppingGoToRecharge,
        States.StoppingPausedMission,
        States.StoppingPausedReturnHome,
    ]:
        return IsarStatus.Stopping
    elif state_name == States.StoppingReturnHome:
        return IsarStatus.StoppingReturnHome
    else:
        return IsarStatus.Busy


def read_or_create_persistent_mode() -> RobotStartupMode:
    try:
        startup_mode = read_persistent_robot_state(settings.ISAR_ID)
    except NoSuchRobotException:
        create_persistent_robot_state(
            settings.ISAR_ID,
            RobotStartupMode.Maintenance,
        )
        startup_mode = read_persistent_robot_state(settings.ISAR_ID)
        logger = logging.getLogger("state_machine")
        logger.info(
            f"Created new persistent robot state for robot id {settings.ISAR_ID}. It is now set to: {startup_mode}."
        )
    return startup_mode


@dataclass(frozen=True)
class Edge:
    source: States
    target: States
    trigger: Event[Any] | TimeoutHandler[Any]
    guard: str | None
    entry: str  # e.g. "Monitor.start_mission"


def _entry_names(modules: Iterable[ModuleType]) -> dict[int, str]:
    return {
        id(value): f"{value.state_definition.name.name}.{attribute}"
        for module in modules
        for attribute, value in vars(module).items()
        if isinstance(value, TransitionDef)
    }


def _guard_label(branch: Branch) -> str | None:
    name = getattr(branch.transition_when, "__name__", "<lambda>")
    return None if name in ("<lambda>", "_always") else name


def collect_edges(
    events: Events, modules: Iterable[ModuleType] = STATE_MODULES
) -> list[Edge]:
    """Builds every possible transition from the state definitions, without running any handlers."""
    modules = list(modules)
    entry_names = _entry_names(modules)
    edges: list[Edge] = []

    for module in modules:
        state = module.state
        triggers: list[tuple[Event[Any] | TimeoutHandler[Any], tuple[Branch, ...]]] = [
            (on.event(events), on.branches) for on in state.handlers()
        ]
        triggers += [(timer, timer.branches) for timer in state.timers()]

        for trigger, branches in triggers:
            for branch in branches:
                edges.append(
                    Edge(
                        source=state.name,
                        target=branch.transition.state_definition.name,
                        trigger=trigger,
                        guard=_guard_label(branch),
                        entry=entry_names.get(id(branch.transition), "<unnamed entry>"),
                    )
                )

    return edges


def adjacency(edges: Iterable[Edge]) -> dict[States, set[States]]:
    graph: dict[States, set[States]] = {state: set() for state in States}
    for edge in edges:
        graph[edge.source].add(edge.target)
    return graph


def _trigger_label(trigger: Event[Any] | TimeoutHandler[Any]) -> str:
    if isinstance(trigger, TimeoutHandler):
        return f"after {trigger.timeout_in_seconds}s ({trigger.name})"
    return trigger.name


def to_mermaid(edges: Iterable[Edge], initial: States = States.UnknownStatus) -> str:
    lines = ["stateDiagram", f"    [*] --> {initial.name}"]
    for edge in edges:
        label = _trigger_label(edge.trigger)
        if edge.guard is not None:
            label += f" [{edge.guard}]"
        lines.append(f"    {edge.source.name} --> {edge.target.name}: {label}")
    return "\n".join(lines)
