import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
)
from isar.state_machine.states_enum import States


def _reject_maintenance(events: OutputEvents, _: str | None, __: EmptyMessage) -> None:
    events.api.respond(
        lambda r: r.set_maintenance_mode,
        MaintenanceResponse(
            is_maintenance_mode=False,
            failure_reason="Failed to stop ongoing mission",
        ),
    )


def _publish_stopped(
    events: OutputEvents,
    mission_id: str | None,
    stop_result: AbortedMission | MissionCompleted | EmptyMessage,
) -> None:
    if isinstance(stop_result, MissionCompleted) and mission_id:
        events.mqtt.publish_mission_status(mission_id, stop_result.status, None)
    elif mission_id:
        events.mqtt.publish_mission_aborted(
            mission_id, "Mission aborted, robot being sent to maintenance"
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
                    side_effect=_publish_stopped,
                ),
            ),
        ),
    ),
)


def _request_stop(events: OutputEvents, _: str | None) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())


transition_and_stop_mission: TransitionDef[str | None, str | None] = TransitionDef(
    state, forward, side_effect=_request_stop
)
