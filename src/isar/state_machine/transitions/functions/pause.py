from typing import TYPE_CHECKING

from isar.apis.models.models import ControlMissionResponse

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def trigger_pause_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.pause_mission.trigger_event(True)
    return True


def pause_mission_failed(state_machine: "StateMachine") -> bool:
    state_machine.events.api_requests.pause_mission.response.trigger_event(
        ControlMissionResponse(
            success=False, failure_reason="Failed to pause mission in ISAR"
        )
    )
    return True


def pause_return_home_mission_failed(state_machine: "StateMachine") -> bool:
    if state_machine.events.api_requests.start_mission.request.has_event():
        return True
    paused_mission_response: ControlMissionResponse = ControlMissionResponse(
        success=False, failure_reason="ISAR failed to pause return home"
    )
    state_machine.events.api_requests.pause_mission.response.trigger_event(
        paused_mission_response
    )
    return True
