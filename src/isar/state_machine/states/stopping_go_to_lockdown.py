import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
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

type StopResult = AbortedMission | MissionCompleted | EmptyMessage


def _reject_lockdown(events: OutputEvents, _: str, __: EmptyMessage) -> None:
    events.api.respond(
        lambda r: r.send_to_lockdown,
        LockdownResponse(
            lockdown_started=False,
            failure_reason="Failed to stop ongoing mission",
        ),
    )


def _publish_completed(
    events: OutputEvents, mission_id: str, stop_result: StopResult
) -> None:
    if isinstance(stop_result, MissionCompleted) and mission_id:
        events.mqtt.publish_mission_status(mission_id, stop_result.status, None)


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
                    side_effect=_reject_lockdown,
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
                    side_effect=_publish_completed,
                ),
            ),
        ),
    ),
)


def _request_stop(events: OutputEvents, _: str) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())


transition_and_stop_mission: TransitionDef[str, str] = TransitionDef(
    state, forward, side_effect=_request_stop
)
