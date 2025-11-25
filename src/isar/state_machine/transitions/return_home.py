from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def get_return_home_transitions(state_machine: "StateMachine") -> List[dict]:
    return_home_transitions: List[dict] = [
        {
            "trigger": "start_return_home_monitoring",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.home_state,
                state_machine.intervention_needed_state,
                state_machine.monitor_state,
                state_machine.stopping_state,
                state_machine.stopping_return_home_state,
                state_machine.stopping_paused_mission_state,
                state_machine.stopping_paused_return_home_state,
            ],
            "dest": state_machine.returning_home_state,
        },
        {
            "trigger": "returned_home",
            "source": state_machine.returning_home_state,
            "dest": state_machine.home_state,
        },
        {
            "trigger": "starting_recharging",
            "source": [
                state_machine.lockdown_state,
                state_machine.home_state,
                state_machine.going_to_recharging_state,
            ],
            "dest": state_machine.recharging_state,
        },
        {
            "trigger": "return_home_failed",
            "source": [
                state_machine.returning_home_state,
                state_machine.going_to_recharging_state,
            ],
            "dest": state_machine.intervention_needed_state,
        },
        {
            "trigger": "release_intervention_needed",
            "source": state_machine.intervention_needed_state,
            "dest": state_machine.unknown_status_state,
        },
        {
            "trigger": "start_lockdown_mission_monitoring",
            "source": [
                state_machine.stopping_go_to_lockdown_state,
                state_machine.await_next_mission_state,
            ],
            "dest": state_machine.going_to_lockdown_state,
        },
        {
            "trigger": "start_recharging_mission_monitoring",
            "source": [
                state_machine.stopping_go_to_recharge_state,
                state_machine.await_next_mission_state,
            ],
            "dest": state_machine.going_to_recharging_state,
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
        },
        {
            "trigger": "release_from_lockdown",
            "source": state_machine.lockdown_state,
            "dest": state_machine.home_state,
        },
        {
            "trigger": "go_to_home",
            "source": state_machine.intervention_needed_state,
            "dest": state_machine.home_state,
        },
    ]
    return return_home_transitions
