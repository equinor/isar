import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
import isar.state_machine.states.unknown_status as UnknownStatus
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
from robot_interface.models.mission.status import RobotStatus


def _clear_robot_status(events: OutputEvents, _: None) -> None:
    # Avoids reading an outdated robot status after entering
    events.robot.clear_robot_status()


state: StateDef[None] = StateDef(
    name=States.Home,
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
            event=lambda e: e.robot_async_events.robot_status_update,
            branches=(
                Branch(
                    AwaitNextMission.transition,
                    transition_when=lambda _, s: s == RobotStatus.Available,
                ),
                Branch(
                    Offline.transition,
                    transition_when=lambda _, s: s == RobotStatus.Offline,
                ),
                Branch(
                    Maintenance.transition,
                    transition_when=lambda _, s: s == RobotStatus.TeleOperation,
                ),
                Branch(
                    UnknownStatus.transition,
                    transition_when=lambda _, s: s != RobotStatus.Home,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(Branch(Lockdown.transition_and_respond_to_api),),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.battery_below_mission_threshold,
            branches=(Branch(Recharging.transition),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(Maintenance.transition_and_respond_to_api),),
        ),
    ),
)

transition: TransitionDef[None, None] = TransitionDef(
    state, forward, side_effect=_clear_robot_status
)
