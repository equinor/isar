import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.going_to_recharging_with_mission as GoingToRechargingWithMission
import isar.state_machine.states.intervention_needed as InterventionNeeded
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
    forward_transition_parameter,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus


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
    name=States.StoppingGoToRecharge,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to stop mission when battery was low",
                    side_effects=(
                        HandlerEffect(
                            OutputEvent.mqtt(lambda q: q.publish_mission_result),
                            lambda mission_id, _: MissionResultStatus(
                                mission_id, MissionStatus.Failed
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
                    GoingToRechargingWithMission.transition_and_start_return_home,
                    _aborted_mission,
                    transition_when=_was_aborted,
                ),
                Branch(
                    GoingToRecharging.transition_and_start_return_home,
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
