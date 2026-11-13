import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.recharging_with_mission as RechargingWithMission
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage
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
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus


def _publish_mission_failed(
    events: OutputEvents, mission: AbortedMission, error: ErrorMessage
) -> None:
    events.mqtt.publish_mission_status(mission.id, MissionStatus.Failed, error)


def _accept_stop(events: OutputEvents, _: AbortedMission, __: EmptyMessage) -> None:
    events.api.respond(lambda r: r.stop_mission, ControlMissionResponse(success=True))


state: StateDef[AbortedMission] = StateDef(
    name=States.GoingToRechargingWithMission,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.return_home.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Return home to recharge failed",
                    side_effect=_publish_mission_failed,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.return_home.success,
            branches=(
                Branch(RechargingWithMission.transition, forward_state_parameter),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    GoingToLockdownWithMission.transition_with_existing_return_home_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    GoingToRecharging.transition_with_existing_return_home,
                    side_effect=_accept_stop,
                ),
            ),
        ),
    ),
)


def _request_return_home(events: OutputEvents, _: AbortedMission) -> None:
    events.robot.request(lambda a: a.return_home, EmptyMessage())


transition_and_start_return_home: TransitionDef[AbortedMission, AbortedMission] = (
    TransitionDef(state, forward, side_effect=_request_return_home)
)
