import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
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


def _completed_mission_status(
    mission_id: str, stop_result: AbortedMission | MissionCompleted
) -> MissionResultStatus:
    assert isinstance(stop_result, MissionCompleted)
    return MissionResultStatus(mission_id, stop_result.status)


def _was_aborted(_: str, stop_result: AbortedMission | MissionCompleted) -> bool:
    return isinstance(stop_result, AbortedMission)


def _aborted_mission(
    _: str, stop_result: AbortedMission | MissionCompleted
) -> AbortedMission:
    assert isinstance(stop_result, AbortedMission)
    return stop_result


state: StateDef[str] = StateDef(
    name=States.StoppingGoToLockdown,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    Monitor.transition_with_existing_mission,
                    forward_state_parameter,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.api_response(lambda a: a.send_to_lockdown),
                            lambda _, __: LockdownResponse(
                                lockdown_started=False,
                                failure_reason="Failed to stop ongoing mission",
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
                    GoingToLockdownWithMission.transition_and_start_return_home_and_respond_to_api,
                    _aborted_mission,
                    transition_when=_was_aborted,
                ),
                Branch(
                    GoingToLockdown.transition_and_start_return_home_and_respond_to_api,
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            _completed_mission_status,
                        ),
                    ),
                ),
            ),
        ),
    ),
)


transition_and_stop_mission: TransitionDef[str, str] = TransitionDef(
    state,
    forward_transition_parameter,
    side_effects=(
        TransitionEffect(
            OutputEvent.robot_request(lambda a: a.stop_mission),
            lambda _: EmptyMessage(),
        ),
    ),
)
