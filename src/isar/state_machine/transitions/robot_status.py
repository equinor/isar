from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def get_robot_status_transitions(state_machine: "StateMachine") -> List[dict]:
    robot_status_transitions: List[dict] = [
        {
            "trigger": "initial_transition",
            "source": state_machine.unknown_status_state,
            "dest": state_machine.unknown_status_state,
        },
        {
            "trigger": "initial_transition",
            "source": state_machine.maintenance_state,
            "dest": state_machine.maintenance_state,
        },
        {
            "trigger": "robot_status_available",
            "source": [
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "robot_status_available",
            "source": [
                state_machine.offline_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.home_state,
            ],
            "dest": state_machine.intervention_needed_state,
        },
        {
            "trigger": "robot_status_home",
            "source": [
                state_machine.home_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.offline_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.home_state,
        },
        {
            "trigger": "robot_status_blocked_protective_stop",
            "source": [
                state_machine.home_state,
                state_machine.offline_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.blocked_protective_stopping_state,
        },
        {
            "trigger": "robot_status_offline",
            "source": [
                state_machine.home_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.unknown_status_state,
                state_machine.recharging_state,
            ],
            "dest": state_machine.offline_state,
        },
        {
            "trigger": "robot_status_unknown",
            "source": [
                state_machine.home_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.offline_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.unknown_status_state,
        },
        {
            "trigger": "robot_status_busy",
            "source": [
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.stopping_state,
        },
        {
            "trigger": "robot_recharged",
            "source": state_machine.recharging_state,
            "dest": state_machine.home_state,
        },
    ]
    return robot_status_transitions
