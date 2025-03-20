from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.fail_mission import (
    report_failed_mission_and_finalize,
)
from isar.state_machine.transitions.functions.return_home import (
    return_home_finished,
    set_return_home_status,
    start_return_home_mission,
)
from isar.state_machine.transitions.functions.start_mission import (
    initialize_robot,
    trigger_start_mission_event,
)
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
                state_machine.robot_standing_still_state,
            ],
            "dest": state_machine.returning_home_state,
            "conditions": [
                def_transition(state_machine, start_return_home_mission),
                def_transition(state_machine, set_return_home_status),
                def_transition(state_machine, initialize_robot),
            ],
            "before": def_transition(state_machine, trigger_start_mission_event),
        },
        {
            "trigger": "request_return_home",
            "source": state_machine.await_next_mission_state,
            "dest": state_machine.await_next_mission_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "request_return_home",
            "source": state_machine.home_state,
            "dest": state_machine.home_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "request_return_home",
            "source": state_machine.robot_standing_still_state,
            "dest": state_machine.robot_standing_still_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "returned_home",
            "source": state_machine.returning_home_state,
            "dest": state_machine.home_state,
            "before": def_transition(state_machine, return_home_finished),
        },
        {
            "trigger": "return_home_failed",
            "source": state_machine.returning_home_state,
            "dest": state_machine.robot_standing_still_state,
            "before": def_transition(state_machine, return_home_finished),
        },
    ]
    return return_home_transitions
