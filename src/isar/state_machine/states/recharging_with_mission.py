from typing import Any

import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission
from isar.models.mqtt_queue import MissionResultStatus
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    HandlerEffect,
    StateDef,
    TransitionDef,
    forward_state_parameter,
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus, RobotStatus

_report_mission_cancelled: HandlerEffect[AbortedMission, Any] = HandlerEffect(
    OutputEvent.mqtt(lambda q: q.publish_mission_result),
    lambda mission, _: MissionResultStatus(mission.id, MissionStatus.Cancelled),
)
_report_mission_failed: HandlerEffect[AbortedMission, Any] = HandlerEffect(
    OutputEvent.mqtt(lambda q: q.publish_mission_result),
    lambda mission, _: MissionResultStatus(mission.id, MissionStatus.Failed),
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
                    side_effects=(_report_mission_failed,),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    Lockdown.transition_and_respond_to_api,
                    side_effects=(_report_mission_cancelled,),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(
                Branch(
                    Maintenance.transition_and_respond_to_api,
                    side_effects=(_report_mission_cancelled,),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    Recharging.transition,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.api_response(lambda a: a.stop_mission),
                            lambda _, __: ControlMissionResponse(success=True),
                        ),
                        _report_mission_cancelled,
                    ),
                ),
            ),
        ),
    ),
)

transition: TransitionDef[AbortedMission, AbortedMission] = TransitionDef(
    state, forward_transition_parameter
)
