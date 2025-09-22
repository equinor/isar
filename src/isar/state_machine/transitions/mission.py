from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.fail_mission import (
    report_failed_mission_and_finalize,
)
from isar.state_machine.transitions.functions.finish_mission import finish_mission
from isar.state_machine.transitions.functions.pause import (
    pause_mission_failed,
    trigger_pause_mission_event,
)
from isar.state_machine.transitions.functions.resume import resume_mission
from isar.state_machine.transitions.functions.return_home import (
    reset_return_home_failure_counter,
    return_home_finished,
)
from isar.state_machine.transitions.functions.start_mission import (
    acknowledge_mission,
    initialize_robot,
    prepare_state_machine_before_mission,
    set_mission_to_in_progress,
    trigger_start_mission_event,
)
from isar.state_machine.transitions.functions.stop import (
    stop_mission_failed,
    stop_return_home_mission_failed,
    trigger_stop_mission_event,
)
from isar.state_machine.transitions.functions.utils import def_transition

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def get_mission_transitions(state_machine: "StateMachine") -> List[dict]:
    mission_transitions: List[dict] = [
        {
            "trigger": "pause",
            "source": state_machine.monitor_state,
            "dest": state_machine.pausing_state,
            "conditions": def_transition(state_machine, trigger_pause_mission_event),
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
            "before": def_transition(state_machine, pause_mission_failed),
        },
        {
            "trigger": "pause_return_home",
            "source": state_machine.returning_home_state,
            "dest": state_machine.pausing_return_home_state,
            "before": [
                def_transition(state_machine, trigger_pause_mission_event),
                def_transition(state_machine, reset_return_home_failure_counter),
            ],
        },
        {
            "trigger": "return_home_mission_pausing_failed",
            "source": state_machine.pausing_return_home_state,
            "dest": state_machine.returning_home_state,
            "before": def_transition(state_machine, stop_return_home_mission_failed),
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
            "before": def_transition(state_machine, trigger_stop_mission_event),
        },
        {
            "trigger": "stop_go_to_lockdown",
            "source": [
                state_machine.monitor_state,
            ],
            "dest": state_machine.stopping_go_to_lockdown_state,
            "before": def_transition(state_machine, trigger_stop_mission_event),
        },
        {
            "trigger": "stop_return_home",
            "source": [
                state_machine.returning_home_state,
                state_machine.return_home_paused_state,
            ],
            "dest": state_machine.stopping_return_home_state,
            "before": [
                def_transition(state_machine, trigger_stop_mission_event),
                def_transition(state_machine, reset_return_home_failure_counter),
                def_transition(state_machine, return_home_finished),
            ],
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
            "before": def_transition(state_machine, stop_mission_failed),
        },
        {
            "trigger": "mission_stopping_failed",
            "source": state_machine.stopping_go_to_lockdown_state,
            "dest": state_machine.monitor_state,
        },
        {
            "trigger": "return_home_mission_stopping_failed",
            "source": state_machine.stopping_return_home_state,
            "dest": state_machine.returning_home_state,
            "before": def_transition(state_machine, stop_return_home_mission_failed),
        },
        {
            "trigger": "request_mission_start",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.home_state,
                state_machine.stopping_return_home_state,
            ],
            "dest": state_machine.monitor_state,
            "prepare": def_transition(state_machine, acknowledge_mission),
            "conditions": [
                def_transition(state_machine, prepare_state_machine_before_mission),
                def_transition(state_machine, initialize_robot),
            ],
            "before": [
                def_transition(state_machine, set_mission_to_in_progress),
                def_transition(state_machine, trigger_start_mission_event),
            ],
        },
        {
            "trigger": "request_mission_start",
            "source": state_machine.await_next_mission_state,
            "dest": state_machine.await_next_mission_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "request_mission_start",
            "source": state_machine.home_state,
            "dest": state_machine.home_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "mission_failed_to_start",
            "source": [state_machine.monitor_state, state_machine.returning_home_state],
            "dest": state_machine.await_next_mission_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "mission_finished",
            "source": state_machine.monitor_state,
            "dest": state_machine.await_next_mission_state,
            "before": def_transition(state_machine, finish_mission),
        },
        {
            "trigger": "lock_down_successful",
            "source": state_machine.going_to_lockdown_state,
            "dest": state_machine.lockdown_state,
            "before": def_transition(state_machine, finish_mission),
        },
    ]
    return mission_transitions
