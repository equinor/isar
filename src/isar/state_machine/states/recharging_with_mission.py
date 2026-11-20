import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage
from isar.models.mqtt_queue import MissionStatusUpdate
from isar.state_machine.output_events import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward_state_parameter,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus, RobotStatus


def _accept_stop(
    events: OutputEvents, mission: AbortedMission, __: EmptyMessage
) -> None:
    events.api.respond(lambda r: r.stop_mission, ControlMissionResponse(success=True))
    events.mqtt.publish_mission_result(
        MissionStatusUpdate(mission.id, MissionStatus.Cancelled)
    )


def _report_mission_cancelled(
    events: OutputEvents, mission: AbortedMission, __: EmptyMessage
) -> None:
    events.mqtt.publish_mission_result(
        MissionStatusUpdate(mission.id, MissionStatus.Cancelled)
    )


def _report_mission_failed(
    events: OutputEvents, mission: AbortedMission, __: EmptyMessage
) -> None:
    events.mqtt.publish_mission_result(
        MissionStatusUpdate(mission.id, MissionStatus.Failed)
    )


state: StateDef[AbortedMission] = StateDef(
    name=States.RechargingWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.robot_async_events.battery_above_recharge_threshold,
            branches=(
                Branch(Monitor.transition_and_start_mission, forward_state_parameter),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.robot_status_update,
            branches=(
                Branch(
                    Offline.transition,
                    transition_when=lambda _, s: s == RobotStatus.Offline,
                    side_effect=_report_mission_failed,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    Lockdown.transition_and_respond_to_api,
                    side_effect=_report_mission_cancelled,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    side_effect=_report_mission_cancelled,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(Branch(Recharging.transition, side_effect=_accept_stop),),
        ),
    ),
)

transition: TransitionDef[AbortedMission, AbortedMission] = TransitionDef(
    state, forward_transition_parameter
)
