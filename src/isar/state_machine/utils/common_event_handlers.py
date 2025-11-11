from typing import TYPE_CHECKING, Callable, Optional

from isar.apis.models.models import ControlMissionResponse, MissionStartResponse
from isar.models.events import Event
from robot_interface.models.mission.mission import Mission

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def start_mission_event_handler(
    state_machine: "StateMachine",
    event: Event[Mission],
    response: Event[MissionStartResponse],
) -> Optional[Callable]:
    mission: Optional[Mission] = event.consume_event()
    if not mission:
        return None

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
    return state_machine.start_mission_monitoring  # type: ignore


def return_home_event_handler(
    state_machine: "StateMachine", event: Event[bool]
) -> Optional[Callable]:
    if not event.consume_event():
        return None

    state_machine.events.api_requests.return_home.response.trigger_event(True)
    state_machine.start_return_home_mission()
    return state_machine.start_return_home_monitoring  # type: ignore


def stop_mission_event_handler(
    state_machine: "StateMachine", event: Event[str]
) -> Optional[Callable]:
    mission_id: str = event.consume_event()
    if mission_id is None:
        return None

    if state_machine.shared_state.mission_id.check() == mission_id or mission_id == "":
        state_machine.events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=True)
        )
        state_machine.events.state_machine_events.stop_mission.trigger_event(True)
        return state_machine.stop  # type: ignore
    else:
        state_machine.events.api_requests.stop_mission.response.trigger_event(
            ControlMissionResponse(success=False, failure_reason="Mission not found")
        )
        return None


def mission_started_event_handler(
    state_machine: "StateMachine",
    event: Event[bool],
) -> Optional[Callable]:
    if not event.consume_event():
        return None

    state_machine.logger.info("Received confirmation that mission has started")
    return None
