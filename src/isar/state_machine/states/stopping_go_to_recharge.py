import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.going_to_recharging_with_mission as GoingToRechargingWithMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.models.events import AbortedMission, EmptyMessage, MissionCompleted
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

type StopResult = AbortedMission | MissionCompleted | EmptyMessage


def _publish_completed(
    events: OutputEvents, mission_id: str, stop_result: StopResult
) -> None:
    assert isinstance(stop_result, MissionCompleted)
    events.mqtt.publish_mission_status(mission_id, stop_result.status, None)


def _publish_cancelled(events: OutputEvents, mission_id: str, _: StopResult) -> None:
    events.mqtt.publish_mission_status(mission_id, MissionStatus.Cancelled, None)


def _publish_failed(events: OutputEvents, mission_id: str, _: EmptyMessage) -> None:
    events.mqtt.publish_mission_status(mission_id, MissionStatus.Failed, None)


def _was_aborted(_: str, stop_result: StopResult) -> bool:
    return isinstance(stop_result, AbortedMission)


def _stopped_mission_not_monitored(_: str, stop_result: StopResult) -> bool:
    return isinstance(stop_result, EmptyMessage)


def _aborted_mission(_: str, stop_result: StopResult) -> AbortedMission:
    assert isinstance(stop_result, AbortedMission)
    return stop_result


state: StateDef[str] = StateDef(
    name=States.StoppingGoToRecharge,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop mission when battery was low",
                    side_effect=_publish_failed,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(
                    GoingToRechargingWithMission.transition_and_start_return_home,
                    _aborted_mission,
                    transition_when=_was_aborted,
                ),
                Branch(
                    GoingToRecharging.transition_and_start_return_home,
                    transition_when=_stopped_mission_not_monitored,
                    side_effect=_publish_cancelled,
                ),
                Branch(
                    GoingToRecharging.transition_and_start_return_home,
                    side_effect=_publish_completed,
                ),
            ),
        ),
    ),
)


def _request_stop(events: OutputEvents, _: str) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())


transition_and_stop_mission: TransitionDef[str, str] = TransitionDef(
    state, forward_transition_parameter, side_effect=_request_stop
)
