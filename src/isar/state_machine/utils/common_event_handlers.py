from typing import TYPE_CHECKING, Optional

import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import MissionStartResponse
from isar.eventhandlers.eventhandler import Transition
from isar.models.events import Event
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def start_mission_event_handler(
    state_machine: "StateMachine",
    mission: Mission,
    response: Event[MissionStartResponse],
) -> Optional[Transition["Monitor.Monitor"]]:
    if not state_machine.battery_level_is_above_mission_start_threshold():
        response.trigger_event(
            MissionStartResponse(
                mission_id=mission.id,
                mission_started=False,
                mission_not_started_reason="Robot battery too low",
            )
        )
        return None
    return Monitor.transition_and_start_mission(mission, True)
