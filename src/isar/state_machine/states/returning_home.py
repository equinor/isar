import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.pausing_return_home as PausingReturnHome
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_return_home as StoppingReturnHome
from isar.config.settings import settings
from isar.models.events import EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
    forward_event,
)
from isar.state_machine.states_enum import States


def initial_retries(_: object, __: object) -> int:
    return settings.RETURN_HOME_RETRY_LIMIT - 1


state: StateDef[int] = StateDef(
    name=States.ReturningHome,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.pause_mission.request,
            branches=(
                Branch(
                    PausingReturnHome.transition_and_pause_return_home_and_respond_to_api
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: f"Return home failed after {settings.RETURN_HOME_RETRY_LIMIT} attempts",
                    transition_when=lambda retries, _: retries < 1,
                ),
                Branch(transition_and_return_home, lambda retries, _: retries - 1),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.start_mission.request,
            branches=(
                Branch(
                    StoppingReturnHome.transition_and_stop_return_home_and_respond_to_api,
                    forward_event,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.success,
            branches=(Branch(Home.transition),),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.battery_below_mission_threshold,
            branches=(Branch(GoingToRecharging.transition_with_existing_return_home),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    GoingToLockdown.transition_with_existing_mission_and_respond_to_api
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(StoppingDueToMaintenance.transition_and_stop_mission),),
        ),
    ),
)


def _request_return_home(events: OutputEvents, _: int) -> None:
    events.robot.request(lambda a: a.return_home, EmptyMessage())


def _request_return_home_and_respond(events: OutputEvents, retries: int) -> None:
    _request_return_home(events, retries)
    events.api.respond(lambda r: r.return_home, EmptyMessage())


transition_and_return_home: TransitionDef[int, int] = TransitionDef(
    state, forward, side_effect=_request_return_home
)
transition_and_return_home_and_respond_to_api: TransitionDef[int, int] = TransitionDef(
    state, forward, side_effect=_request_return_home_and_respond
)
transition_with_existing_mission: TransitionDef[None, int] = TransitionDef(
    state, lambda _: initial_retries(None, None)
)
