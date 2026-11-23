import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
from isar.models.mqtt_queue import MissionAborted, MissionResultStatus
from isar.state_machine.output_events import OutputEvent
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


def _completed_mission_status(
    mission_id: str | None, stop_result: AbortedMission | MissionCompleted
) -> MissionResultStatus:
    assert isinstance(stop_result, MissionCompleted)
    return MissionResultStatus(mission_id, stop_result.status)


def _publish_mission_aborted(
    mission_id: str | None, _: AbortedMission | MissionCompleted
) -> MissionAborted:
    return MissionAborted(
        mission_id,
        "Mission aborted, robot being sent to maintenance",
    )


state: StateDef[str | None] = StateDef(
    name=States.StoppingDueToMaintenance,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop mission when entering maintenance mode",
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.api_response(lambda a: a.set_maintenance_mode),
                            lambda _, __: MaintenanceResponse(
                                is_maintenance_mode=False,
                                failure_reason="Failed to stop ongoing mission",
                            ),
                        ),
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            lambda mission_id, _: MissionResultStatus(
                                mission_id,
                                MissionStatus.Failed,
                            ),
                            when=lambda mission_id, _: mission_id is not None,
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
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            _completed_mission_status,
                            when=lambda mission_id, _: mission_id is not None,
                        ),
                    ),
                ),
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_aborted),
                            _publish_mission_aborted,
                            when=lambda mission_id, _: mission_id is not None,
                        ),
                    ),
                    transition_when=lambda mission_id, _: mission_id is not None,
                ),
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_aborted),
                            _publish_mission_aborted,
                            when=lambda mission_id, _: mission_id is not None,
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
    side_effects=(
        TransitionEffect(
            OutputEvent.robot_request(lambda a: a.stop_mission),
            lambda _: EmptyMessage(),
        ),
    ),
)
