from typing import TYPE_CHECKING

from isar.apis.models.models import ControlMissionResponse

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def trigger_pause_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.pause_mission.trigger_event(True)
    return True


def pause_mission_failed(state_machine: "StateMachine") -> bool:
    paused_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.pause_mission.response.trigger_event(
        paused_mission_response
    )
    return True


def stop_return_home_mission_failed(state_machine: "StateMachine") -> bool:
    paused_mission_response: ControlMissionResponse = (
        state_machine._make_control_mission_response()
    )
    state_machine.events.api_requests.pause_mission.response.trigger_event(
        paused_mission_response
    )
    return True
