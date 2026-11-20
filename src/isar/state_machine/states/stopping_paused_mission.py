import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.paused as Paused
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import EmptyMessage
from isar.models.mqtt_queue import MissionStatusUpdate
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
from robot_interface.models.mission.status import MissionStatus

state: StateDef[str] = StateDef(
    name=States.StoppingPausedMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(Branch(Paused.transition, forward_state_parameter),),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(
                    AwaitNextMission.transition,
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            lambda mission_id, _: MissionStatusUpdate(
                                mission_id, MissionStatus.Cancelled
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
    effects=(
        TransitionEffect(
            lambda e: e.action_requests.stop_mission.trigger_request,
            lambda _: EmptyMessage(),
        ),
        TransitionEffect(
            lambda e: e.api_requests.stop_mission.trigger_response,
            lambda _: ControlMissionResponse(success=True),
        ),
    ),
)
