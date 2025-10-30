from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.resume import resume_mission
from isar.state_machine.transitions.functions.return_home import (
    reset_return_home_failure_counter,
)
from isar.state_machine.transitions.functions.start_mission import initialize_robot
from isar.state_machine.transitions.functions.utils import def_transition

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def get_mission_transitions(state_machine: "StateMachine") -> List[dict]:
    mission_transitions: List[dict] = [
        {
            "trigger": "pause",
            "source": state_machine.monitor_state,
            "dest": state_machine.pausing_state,
        },
        {
            "trigger": "mission_paused",
            "source": state_machine.pausing_state,
            "dest": state_machine.paused_state,
        },
        {
            "trigger": "mission_pausing_failed",
            "source": state_machine.pausing_state,
            "dest": state_machine.monitor_state,
        },
        {
            "trigger": "pause_return_home",
            "source": state_machine.returning_home_state,
            "dest": state_machine.pausing_return_home_state,
            "before": [
                def_transition(state_machine, reset_return_home_failure_counter),
            ],
        },
        {
            "trigger": "return_home_mission_pausing_failed",
            "source": state_machine.pausing_return_home_state,
            "dest": state_machine.returning_home_state,
        },
        {
            "trigger": "return_home_mission_paused",
            "source": state_machine.pausing_return_home_state,
            "dest": state_machine.return_home_paused_state,
        },
        {
            "trigger": "resume",
            "source": state_machine.paused_state,
            "dest": state_machine.monitor_state,
            "conditions": def_transition(state_machine, resume_mission),
        },
        {
            "trigger": "resume",
            "source": state_machine.paused_state,
            "dest": state_machine.paused_state,
        },
        {
            "trigger": "resume",
            "source": state_machine.return_home_paused_state,
            "dest": state_machine.returning_home_state,
            "conditions": def_transition(state_machine, resume_mission),
        },
        {
            "trigger": "resume",
            "source": state_machine.return_home_paused_state,
            "dest": state_machine.return_home_paused_state,
        },
        {
            "trigger": "resume_lockdown",
            "source": state_machine.return_home_paused_state,
            "dest": state_machine.going_to_lockdown_state,
            "conditions": def_transition(state_machine, resume_mission),
        },
        {
            "trigger": "stop",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.monitor_state,
                state_machine.paused_state,
            ],
            "dest": state_machine.stopping_state,
        },
        {
            "trigger": "stop_go_to_lockdown",
            "source": [
                state_machine.monitor_state,
            ],
            "dest": state_machine.stopping_go_to_lockdown_state,
        },
        {
            "trigger": "stop_go_to_recharge",
            "source": state_machine.monitor_state,
            "dest": state_machine.stopping_go_to_recharge_state,
        },
        {
            "trigger": "stop_return_home",
            "source": [
                state_machine.returning_home_state,
                state_machine.return_home_paused_state,
            ],
            "dest": state_machine.stopping_return_home_state,
            "before": def_transition(state_machine, reset_return_home_failure_counter),
        },
        {
            "trigger": "mission_stopped",
            "source": state_machine.stopping_state,
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "mission_stopped",
            "source": state_machine.stopping_go_to_lockdown_state,
            "dest": state_machine.going_to_lockdown_state,
        },
        {
            "trigger": "mission_stopping_failed",
            "source": state_machine.stopping_state,
            "dest": state_machine.monitor_state,
        },
        {
            "trigger": "mission_stopping_failed",
            "source": [
                state_machine.stopping_go_to_lockdown_state,
                state_machine.stopping_go_to_recharge_state,
            ],
            "dest": state_machine.monitor_state,
        },
        {
            "trigger": "return_home_mission_stopping_failed",
            "source": state_machine.stopping_return_home_state,
            "dest": state_machine.returning_home_state,
        },
        {
            "trigger": "request_mission_start",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.home_state,
                state_machine.stopping_return_home_state,
            ],
            "dest": state_machine.monitor_state,
            "conditions": [
                def_transition(state_machine, initialize_robot),
            ],
        },
        {
            "trigger": "request_mission_start",
            "source": state_machine.await_next_mission_state,
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "request_mission_start",
            "source": state_machine.home_state,
            "dest": state_machine.home_state,
        },
        {
            "trigger": "mission_failed_to_start",
            "source": [state_machine.monitor_state, state_machine.returning_home_state],
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "mission_finished",
            "source": state_machine.monitor_state,
            "dest": state_machine.await_next_mission_state,
        },
    ]
    return mission_transitions
