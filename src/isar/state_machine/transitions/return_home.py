from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.fail_mission import (
    report_failed_lockdown_and_intervention_needed,
    report_failed_return_home_and_intervention_needed,
)
from isar.state_machine.transitions.functions.return_home import (
    reset_return_home_failure_counter,
    should_retry_return_home,
    start_return_home_mission,
)
from isar.state_machine.transitions.functions.robot_status import clear_robot_status
from isar.state_machine.transitions.functions.start_mission import initialize_robot
from isar.state_machine.transitions.functions.utils import def_transition

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def get_return_home_transitions(state_machine: "StateMachine") -> List[dict]:
    return_home_transitions: List[dict] = [
        {
            "trigger": "request_return_home",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.home_state,
                state_machine.intervention_needed_state,
                state_machine.monitor_state,
                state_machine.stopping_state,
                state_machine.stopping_return_home_state,
            ],
            "dest": state_machine.returning_home_state,
            "before": def_transition(state_machine, start_return_home_mission),
            "conditions": [
                def_transition(state_machine, initialize_robot),
            ],
        },
        {
            "trigger": "request_return_home",
            "source": state_machine.await_next_mission_state,
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "request_return_home",
            "source": state_machine.home_state,
            "dest": state_machine.home_state,
        },
        {
            "trigger": "returned_home",
            "source": state_machine.returning_home_state,
            "dest": state_machine.home_state,
            "before": [
                def_transition(state_machine, clear_robot_status),
                def_transition(state_machine, reset_return_home_failure_counter),
            ],
        },
        {
            "trigger": "returned_home",
            "source": state_machine.returning_home_state,
            "dest": state_machine.intervention_needed_state,
        },
        {
            "trigger": "starting_recharging",
            "source": state_machine.going_to_recharging_state,
            "dest": state_machine.recharging_state,
            "before": [
                def_transition(state_machine, reset_return_home_failure_counter),
            ],
        },
        {
            "trigger": "starting_recharging",
            "source": [state_machine.lockdown_state, state_machine.home_state],
            "dest": state_machine.recharging_state,
        },
        {
            "trigger": "return_home_failed",
            "source": state_machine.returning_home_state,
            "dest": state_machine.returning_home_state,
            "conditions": [
                def_transition(state_machine, should_retry_return_home),
            ],
            "before": [
                def_transition(state_machine, start_return_home_mission),
                def_transition(state_machine, initialize_robot),
            ],
        },
        {
            "trigger": "return_home_failed",
            "source": [
                state_machine.returning_home_state,
                state_machine.going_to_recharging_state,
            ],
            "dest": state_machine.intervention_needed_state,
            "before": [
                def_transition(
                    state_machine, report_failed_return_home_and_intervention_needed
                ),
                def_transition(state_machine, reset_return_home_failure_counter),
            ],
        },
        {
            "trigger": "release_intervention_needed",
            "source": state_machine.intervention_needed_state,
            "dest": state_machine.unknown_status_state,
        },
        {
            "trigger": "request_lockdown_mission",
            "source": [
                state_machine.stopping_go_to_lockdown_state,
                state_machine.await_next_mission_state,
            ],
            "dest": state_machine.going_to_lockdown_state,
            "conditions": [
                def_transition(state_machine, start_return_home_mission),
                def_transition(state_machine, initialize_robot),
            ],
        },
        {
            "trigger": "request_recharging_mission",
            "source": [
                state_machine.stopping_go_to_recharge_state,
                state_machine.await_next_mission_state,
            ],
            "dest": state_machine.going_to_recharging_state,
            "conditions": [
                def_transition(state_machine, start_return_home_mission),
                def_transition(state_machine, initialize_robot),
            ],
        },
        {
            "trigger": "go_to_lockdown",
            "source": [
                state_machine.returning_home_state,
                state_machine.going_to_recharging_state,
            ],
            "dest": state_machine.going_to_lockdown_state,
        },
        {
            "trigger": "go_to_recharging",
            "source": [
                state_machine.returning_home_state,
                state_machine.return_home_paused_state,
                state_machine.home_state,
            ],
            "dest": state_machine.going_to_recharging_state,
        },
        {
            "trigger": "reached_lockdown",
            "source": [
                state_machine.home_state,
                state_machine.going_to_lockdown_state,
                state_machine.recharging_state,
            ],
            "dest": state_machine.lockdown_state,
        },
        {
            "trigger": "lockdown_mission_failed",
            "source": state_machine.going_to_lockdown_state,
            "dest": state_machine.intervention_needed_state,
            "before": [
                def_transition(
                    state_machine, report_failed_lockdown_and_intervention_needed
                ),
            ],
        },
        {
            "trigger": "release_from_lockdown",
            "source": state_machine.lockdown_state,
            "dest": state_machine.home_state,
        },
    ]
    return return_home_transitions
