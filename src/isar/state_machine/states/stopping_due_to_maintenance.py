import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
from isar.models.mqtt_queue import MissionAborted, MissionResultStatus
from isar.state_machine.output_events import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


def _reject_maintenance(
    events: OutputEvents, mission_id: str | None, __: EmptyMessage
) -> None:
    events.api.respond(
        lambda r: r.set_maintenance_mode,
        MaintenanceResponse(
            is_maintenance_mode=False,
            failure_reason="Failed to stop ongoing mission",
        ),
    )
    if mission_id is not None:
        events.mqtt.publish_mission_result(
            MissionResultStatus(mission_id, MissionStatus.Failed)
        )


def _publish_mission_result(
    events: OutputEvents,
    mission_id: str | None,
    stop_result: AbortedMission | MissionCompleted,
) -> None:
    assert isinstance(stop_result, MissionCompleted)
    if mission_id is not None:
        events.mqtt.publish_mission_result(
            MissionResultStatus(mission_id, stop_result.status)
        )


def _publish_mission_aborted(
    events: OutputEvents,
    mission_id: str | None,
    _: AbortedMission | MissionCompleted,
) -> None:
    if mission_id is not None:
        events.mqtt.publish_mission_aborted(
            MissionAborted(
                mission_id, "Mission aborted, robot being sent to maintenance"
            )
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
                    side_effect=_reject_maintenance,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    side_effect=_publish_mission_result,
                    transition_when=lambda _, stop_result: isinstance(
                        stop_result, MissionCompleted
                    ),
                ),
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    side_effect=_publish_mission_aborted,
                ),
            ),
        ),
    ),
)


def _request_stop(events: OutputEvents, _: str | None) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())


transition_and_stop_mission: TransitionDef[str | None, str | None] = TransitionDef(
    state, forward_transition_parameter, side_effect=_request_stop
)
