import isar.state_machine.states.resuming as Resuming
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
import isar.state_machine.states.stopping_paused_mission as StoppingPausedMission
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
    forward_state_parameter,
)
from isar.state_machine.states_enum import States

state: StateDef[str] = StateDef(
    name=States.Paused,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    StoppingPausedMission.transition_and_stop_mission_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.resume_mission.request,
            branches=(
                Branch(
                    Resuming.transition_and_resume_mission_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.battery_below_mission_threshold,
            branches=(
                Branch(
                    StoppingGoToRecharge.transition_and_stop_mission,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    StoppingGoToLockdown.transition_and_stop_mission,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(
                Branch(
                    StoppingDueToMaintenance.transition_and_stop_mission,
                    forward_state_parameter,
                ),
            ),
        ),
    ),
)

transition: TransitionDef[str, str] = TransitionDef(state, forward)
