import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage
from isar.models.mqtt_queue import MissionResultStatus
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    TransitionEffect,
    forward_state_parameter,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.status import MissionStatus

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
                Branch(
                    AwaitNextMission.transition,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            lambda mission_id, _: MissionResultStatus(
                                mission_id,
                                MissionStatus.Cancelled,
                                ErrorMessage(
                                    ErrorReason.RobotActionException,
                                    "Mission stopped by user",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition_and_stop_mission_and_respond_to_api: TransitionDef[str, str] = TransitionDef(
    state,
    forward_transition_parameter,
    side_effects=(
        TransitionEffect(
            OutputEvent.robot_request(lambda a: a.stop_mission),
            lambda _: EmptyMessage(),
        ),
        TransitionEffect(
            OutputEvent.api_response(lambda a: a.stop_mission),
            lambda _: ControlMissionResponse(success=True),
        ),
    ),
)
