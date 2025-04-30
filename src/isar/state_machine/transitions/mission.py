from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.fail_mission import (
    report_failed_mission_and_finalize,
)
from isar.state_machine.transitions.functions.finish_mission import finish_mission
from isar.state_machine.transitions.functions.pause import pause_mission
from isar.state_machine.transitions.functions.resume import resume_mission
from isar.state_machine.transitions.functions.start_mission import (
    initialize_robot,
    initiate_mission,
    put_start_mission_on_queue,
    set_mission_to_in_progress,
    trigger_start_mission_event,
)
from isar.state_machine.transitions.functions.stop import (
    stop_mission_cleanup,
    stop_return_home_mission_cleanup,
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
            "dest": state_machine.paused_state,
            "before": def_transition(state_machine, pause_mission),
        },
        {
            "trigger": "resume",
            "source": state_machine.paused_state,
            "dest": state_machine.monitor_state,
            "before": def_transition(state_machine, resume_mission),
        },
        {
            "trigger": "stop",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.robot_standing_still_state,
                state_machine.monitor_state,
                state_machine.returning_home_state,
                state_machine.paused_state,
            ],
            "dest": state_machine.stopping_state,
            "before": def_transition(state_machine, trigger_stop_mission_event),
        },
        {
            "trigger": "mission_stopped",
            "source": state_machine.stopping_state,
            "dest": state_machine.await_next_mission_state,
            "before": def_transition(state_machine, stop_mission_cleanup),
        },
        {
            "trigger": "return_home_mission_stopped",
            "source": state_machine.stopping_state,
            "dest": state_machine.robot_standing_still_state,
            "before": def_transition(state_machine, stop_return_home_mission_cleanup),
        },
        {
            "trigger": "request_mission_start",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.home_state,
                state_machine.robot_standing_still_state,
            ],
            "dest": state_machine.monitor_state,
            "prepare": def_transition(state_machine, put_start_mission_on_queue),
            "conditions": [
                def_transition(state_machine, initiate_mission),
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
            "source": state_machine.robot_standing_still_state,
            "dest": state_machine.robot_standing_still_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "request_mission_start",
            "source": state_machine.home_state,
            "dest": state_machine.home_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "request_mission_start",
            "source": state_machine.returning_home_state,
            "dest": state_machine.returning_home_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "mission_failed_to_start",
            "source": state_machine.monitor_state,
            "dest": state_machine.robot_standing_still_state,
            "before": def_transition(state_machine, report_failed_mission_and_finalize),
        },
        {
            "trigger": "mission_finished",
            "source": state_machine.monitor_state,
            "dest": state_machine.await_next_mission_state,
            "before": def_transition(state_machine, finish_mission),
        },
    ]
    return mission_transitions
