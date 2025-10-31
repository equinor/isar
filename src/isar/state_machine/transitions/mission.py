from typing import TYPE_CHECKING, List

from isar.state_machine.transitions.functions.finish_mission import finish_mission
from isar.state_machine.transitions.functions.pause import trigger_pause_mission_event
from isar.state_machine.transitions.functions.resume import trigger_resume_mission_event
from isar.state_machine.transitions.functions.return_home import (
    reset_return_home_failure_counter,
)
from isar.state_machine.transitions.functions.robot_status import is_home
from isar.state_machine.transitions.functions.start_mission import (
    acknowledge_mission,
    initialize_robot,
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
        },
        {
            "trigger": "return_home_mission_paused",
            "source": state_machine.pausing_return_home_state,
            "dest": state_machine.return_home_paused_state,
        },
        {
            "trigger": "resume",
            "source": state_machine.paused_state,
            "dest": state_machine.resuming_state,
            "before": def_transition(state_machine, trigger_resume_mission_event),
        },
        {
            "trigger": "mission_resumed",
            "source": state_machine.resuming_state,
            "dest": state_machine.monitor_state,
        },
        {
            "trigger": "mission_resuming_failed",
            "source": state_machine.resuming_state,
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "resume",
            "source": state_machine.return_home_paused_state,
            "dest": state_machine.resuming_return_home_state,
            "before": def_transition(state_machine, trigger_resume_mission_event),
        },
        {
            "trigger": "return_home_mission_resumed",
            "source": state_machine.resuming_return_home_state,
            "dest": state_machine.returning_home_state,
        },
        {
            "trigger": "return_home_mission_resuming_failed",
            "source": state_machine.resuming_return_home_state,
            "dest": state_machine.await_next_mission_state,
        },
        {
            "trigger": "resume_lockdown",
            "source": state_machine.return_home_paused_state,
            "dest": state_machine.going_to_lockdown_state,
            "before": def_transition(state_machine, trigger_resume_mission_event),
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
                state_machine.paused_state,
            ],
            "dest": state_machine.stopping_go_to_lockdown_state,
            "before": def_transition(state_machine, trigger_stop_mission_event),
        },
        {
            "trigger": "stop_go_to_recharge",
            "source": state_machine.monitor_state,
            "dest": state_machine.stopping_go_to_recharge_state,
            "before": def_transition(state_machine, trigger_stop_mission_event),
        },
        {
            "trigger": "stop_due_to_maintenance",
            "source": [
                state_machine.monitor_state,
                state_machine.paused_state,
                # state_machine.pausing_return_home_state,  # Not neccessary since it will become paused and then the maintenance can trigger.
                # state_machine.pausing_state,              # Not neccessary since it will become paused and then the maintenance can trigger.
                state_machine.return_home_paused_state,
                state_machine.returning_home_state,
                # state_machine.stopping_return_home_state, # Not neccessary since it will become monitor and then the maintenance can trigger.
                # state_machine.stopping_state,             # Not neccessary since it will become await next mission and then the maintenance can trigger.
            ],
            "dest": state_machine.stopping_due_to_maintenance_state,
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
            "trigger": "mission_stopped",
            "source": state_machine.stopping_due_to_maintenance_state,
            "dest": state_machine.maintenance_state,
        },
        {
            "trigger": "mission_stopping_failed",
            "source": state_machine.stopping_state,
            "dest": state_machine.monitor_state,
            "before": def_transition(state_machine, stop_mission_failed),
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
            "trigger": "mission_stopping_failed",
            "source": state_machine.stopping_due_to_maintenance_state,
            "dest": state_machine.unknown_status_state,  # We do not know if we need to go to monitor or return_home state
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
            "before": def_transition(state_machine, finish_mission),
        },
        {
            "trigger": "set_maintenance_mode",
            "source": [
                state_machine.await_next_mission_state,
                state_machine.blocked_protective_stopping_state,
                state_machine.home_state,
                state_machine.intervention_needed_state,
                state_machine.offline_state,
                state_machine.recharging_state,
                state_machine.unknown_status_state,
            ],
            "dest": state_machine.maintenance_state,
        },
        {
            "trigger": "release_from_maintenance",
            "source": [
                state_machine.maintenance_state,
            ],
            "dest": state_machine.home_state,
            "conditions": def_transition(state_machine, is_home),
        },
        {
            "trigger": "release_from_maintenance",
            "source": [
                state_machine.maintenance_state,
            ],
            "dest": state_machine.intervention_needed_state,
        },
    ]
    return mission_transitions
