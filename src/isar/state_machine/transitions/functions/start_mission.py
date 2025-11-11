from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.apis.models.models import MissionStartResponse


def acknowledge_mission(state_machine: "StateMachine") -> bool:
    state_machine.events.api_requests.start_mission.response.trigger_event(
        MissionStartResponse(mission_started=True)
    )
    return True
