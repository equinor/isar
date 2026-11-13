import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
    forward_state_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


def _publish_in_progress(
    events: OutputEvents, mission_id: str, _: EmptyMessage
) -> None:
    events.mqtt.publish_mission_status(mission_id, MissionStatus.InProgress, None)


state: StateDef[str] = StateDef(
    name=States.Resuming,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.failure,
            branches=(Branch(Paused.transition, forward_state_parameter),),
        ),
        EventHandler(
            event=lambda e: e.action_requests.resume_mission.success,
            branches=(
                Branch(
                    Monitor.transition_with_existing_mission,
                    forward_state_parameter,
                    side_effect=_publish_in_progress,
                ),
            ),
        ),
    ),
)


def _respond_and_request_resume(events: OutputEvents, _: str) -> None:
    events.api.respond(lambda r: r.resume_mission, ControlMissionResponse(success=True))
    events.robot.request(lambda a: a.resume_mission, EmptyMessage())


transition_and_resume_mission_and_respond_to_api: TransitionDef[str, str] = (
    TransitionDef(state, forward, side_effect=_respond_and_request_resume)
)
