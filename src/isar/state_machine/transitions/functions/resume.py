from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import ControlMissionResponse


def trigger_resume_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.resume_mission.trigger_event(True)
    return True


def resume_mission_failed(state_machine: "StateMachine") -> bool:
    state_machine.events.api_requests.resume_mission.response.trigger_event(
        ControlMissionResponse(
            success=False, failure_reason="Failed to resume mission in ISAR"
        )
    )
    return True
