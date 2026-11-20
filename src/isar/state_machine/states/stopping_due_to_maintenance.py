import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
from isar.models.mqtt_queue import MissionAborted, MissionStatusUpdate
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    TransitionEffect,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus

type StopResult = AbortedMission | MissionCompleted | EmptyMessage


def _completed_mission_status(
    mission_id: str | None, stop_result: StopResult
) -> MissionStatusUpdate:
    assert isinstance(stop_result, MissionCompleted)
    return MissionStatusUpdate(mission_id, stop_result.status)


state: StateDef[str | None] = StateDef(
    name=States.StoppingDueToMaintenance,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop mission when entering maintenance mode",
                    effects=(
                        HandlerEffect(
                            lambda e: e.api_requests.set_maintenance_mode.trigger_response,
                            lambda _, __: MaintenanceResponse(
                                is_maintenance_mode=False,
                                failure_reason="Failed to stop ongoing mission",
                            ),
                        ),
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            lambda mission_id, _: MissionStatusUpdate(
                                mission_id, MissionStatus.Failed
                            ),
                        ),
                    ),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    transition_when=lambda _, stop_result: isinstance(
                        stop_result, MissionCompleted
                    ),
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            _completed_mission_status,
                        ),
                    ),
                ),
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_aborted,
                            lambda mission_id, _: MissionAborted(
                                mission_id,
                                "Mission aborted, robot being sent to maintenance",
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition_and_stop_mission: TransitionDef[str | None, str | None] = TransitionDef(
    state,
    forward_transition_parameter,
    effects=(
        TransitionEffect(
            lambda e: e.action_requests.stop_mission.trigger_request,
            lambda _: EmptyMessage(),
        ),
    ),
)
