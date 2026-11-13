import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
from isar.config.settings import settings
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TimeoutHandler,
    TransitionDef,
    forward,
    forward_event,
)
from isar.state_machine.states_enum import States

state: StateDef[None] = StateDef(
    name=States.AwaitNextMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.start_mission.request,
            branches=(
                Branch(
                    Monitor.transition_and_start_mission_and_respond_to_api,
                    forward_event,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.return_home.request,
            branches=(
                Branch(
                    ReturningHome.transition_and_return_home_and_respond_to_api,
                    ReturningHome.initial_retries,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    StoppingUnknownMission.transition_and_stop_mission_and_respond_to_api
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    GoingToLockdown.transition_and_start_return_home_and_respond_to_api
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.battery_below_mission_threshold,
            branches=(Branch(GoingToRecharging.transition_and_start_return_home),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(Maintenance.transition_and_respond_to_api),),
        ),
    ),
    timers=lambda: (
        TimeoutHandler(
            name="should_return_home_timer",
            timeout_in_seconds=settings.RETURN_HOME_DELAY,
            branches=(
                Branch(
                    ReturningHome.transition_and_return_home,
                    ReturningHome.initial_retries,
                ),
            ),
        ),
    ),
)

transition: TransitionDef[None, None] = TransitionDef(state, forward)
