from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.robot_status import (
    is_available_or_home,
    is_blocked_protective_stop,
    is_offline,
)
from isar.state_machine.transitions.functions.utils import def_transition

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def get_robot_status_transitions(state_machine: "StateMachine") -> List[dict]:
    robot_status_transitions: List[dict] = [
        {
            "trigger": "robot_status_changed",
            "source": [
                state_machine.home_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.offline_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.home_state,
            "conditions": def_transition(state_machine, is_available_or_home),
        },
        {
            "trigger": "robot_status_changed",
            "source": [
                state_machine.home_state,
                state_machine.offline_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.blocked_protective_stopping_state,
            "conditions": def_transition(state_machine, is_blocked_protective_stop),
        },
        {
            "trigger": "robot_status_changed",
            "source": [
                state_machine.home_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.offline_state,
            "conditions": def_transition(state_machine, is_offline),
        },
        {
            "trigger": "robot_status_changed",
            "source": [
                state_machine.home_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.offline_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.unknown_status_state,
        },
        {
            "trigger": "robot_went_offline",
            "source": [state_machine.recharging_state],
            "dest": state_machine.offline_state,
        },
        {
            "trigger": "robot_recharged",
            "source": [state_machine.recharging_state],
            "dest": state_machine.home_state,
        },
    ]
    return robot_status_transitions
