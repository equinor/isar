import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
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

type StopResult = AbortedMission | MissionCompleted | EmptyMessage


def _is_completed(mission_id: str, stop_result: StopResult) -> bool:
    return isinstance(stop_result, MissionCompleted) and bool(mission_id)


def _completed_mission_status(
    mission_id: str, stop_result: StopResult
) -> MissionStatusUpdate:
    assert isinstance(stop_result, MissionCompleted)
    return MissionStatusUpdate(mission_id, stop_result.status)


def _was_aborted(_: str, stop_result: StopResult) -> bool:
    return isinstance(stop_result, AbortedMission)


def _aborted_mission(_: str, stop_result: StopResult) -> AbortedMission:
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
                    effects=(
                        HandlerEffect(
                            lambda e: e.api_requests.send_to_lockdown.trigger_response,
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
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            _completed_mission_status,
                            when=_is_completed,
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
    effects=(
        TransitionEffect(
            lambda e: e.action_requests.stop_mission.trigger_request,
            lambda _: EmptyMessage(),
        ),
    ),
)
