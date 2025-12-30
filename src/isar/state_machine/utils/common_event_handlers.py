from typing import TYPE_CHECKING, Optional

import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping as Stopping
from isar.apis.models.models import ControlMissionResponse, MissionStartResponse
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
    state_machine.start_mission(mission=mission)
    response.trigger_event(MissionStartResponse(mission_started=True))
    return Monitor.transition(mission.id)


def return_home_event_handler(
    state_machine: "StateMachine", should_return_home: bool
) -> Optional[Transition["ReturningHome.ReturningHome"]]:
    state_machine.events.api_requests.return_home.response.trigger_event(True)
    state_machine.start_return_home_mission()
    return ReturningHome.transition()


def stop_mission_event_handler(
    state_machine: "StateMachine", mission_id: str, current_mission_id: Optional[str]
) -> Optional[Transition["Stopping.Stopping"]]:
    if current_mission_id == mission_id or mission_id == "":
        state_machine.events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        state_machine.events.state_machine_events.stop_mission.trigger_event(True)
        return Stopping.transition(current_mission_id)
    else:
        state_machine.events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=False, failure_reason="Mission not found")
        )
        return None


def mission_started_event_handler(
    state_machine: "StateMachine",
    mission_has_started: bool,
) -> None:
    state_machine.logger.info("Received confirmation that mission has started")
    return None


def successful_stop_return_home_event_handler(
    state_machine: "StateMachine", has_stopped: bool, mission: Mission
) -> Transition["Monitor.Monitor"]:
    state_machine.start_mission(mission=mission)
    state_machine.events.api_requests.start_mission.response.trigger_event(
        MissionStartResponse(mission_started=True)
    )
    return Monitor.transition(mission.id)
