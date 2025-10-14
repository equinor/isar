from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import ControlMissionResponse


def trigger_stop_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.stop_mission.trigger_event(True)
    return True


def stop_mission_failed(state_machine: "StateMachine") -> bool:
    stopped_mission_response: ControlMissionResponse = ControlMissionResponse(
        success=False, failure_reason="ISAR failed to stop mission"
    )
    state_machine.events.api_requests.stop_mission.response.trigger_event(
        stopped_mission_response
    )
    return True


def stop_return_home_mission_failed(state_machine: "StateMachine") -> bool:
    if state_machine.events.api_requests.start_mission.request.has_event():
        return True
    stopped_mission_response: ControlMissionResponse = ControlMissionResponse(
        success=False, failure_reason="ISAR failed to stop return home"
    )
    state_machine.events.api_requests.stop_mission.response.trigger_event(
        stopped_mission_response
    )
    return True
