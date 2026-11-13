import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
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
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus


def _publish_cancelled(
    events: OutputEvents,
    mission_id: str,
    _: AbortedMission | MissionCompleted | EmptyMessage,
) -> None:
    events.mqtt.publish_mission_status(
        mission_id,
        MissionStatus.Cancelled,
        ErrorMessage(ErrorReason.RobotActionException, "Mission stopped by user"),
    )


state: StateDef[str] = StateDef(
    name=States.Stopping,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    Monitor.transition_with_existing_mission, forward_state_parameter
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(AwaitNextMission.transition, side_effect=_publish_cancelled),
            ),
        ),
    ),
)


def _request_stop_and_respond(events: OutputEvents, _: str) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())
    events.api.respond(lambda r: r.stop_mission, ControlMissionResponse(success=True))


transition_and_stop_mission_and_respond_to_api: TransitionDef[str, str] = TransitionDef(
    state, forward, side_effect=_request_stop_and_respond
)
