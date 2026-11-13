import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.pausing as Pausing
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
from isar.apis.models.models import MissionStartResponse
from isar.models.events import EmptyMessage
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
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus


def _publish_mission_successful(
    events: OutputEvents, mission_id: str, _: EmptyMessage
) -> None:
    events.mqtt.publish_mission_status(mission_id, MissionStatus.Successful, None)


def _publish_mission_failed(
    events: OutputEvents, mission_id: str, error: ErrorMessage
) -> None:
    events.mqtt.publish_mission_status(mission_id, MissionStatus.Failed, error)


state: StateDef[str] = StateDef(
    name=States.Monitor,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.stop_mission.request,
            branches=(
                Branch(
                    Stopping.transition_and_stop_mission_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.pause_mission.request,
            branches=(
                Branch(
                    Pausing.transition_and_pause_mission_and_respond_to_api,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.execute_mission.failure,
            branches=(
                Branch(
                    AwaitNextMission.transition,
                    side_effect=_publish_mission_failed,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.execute_mission.success,
            branches=(
                Branch(
                    AwaitNextMission.transition,
                    side_effect=_publish_mission_successful,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.battery_below_mission_threshold,
            branches=(
                Branch(
                    StoppingGoToRecharge.transition_and_stop_mission,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    StoppingGoToLockdown.transition_and_stop_mission,
                    forward_state_parameter,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(
                Branch(
                    StoppingDueToMaintenance.transition_and_stop_mission,
                    forward_state_parameter,
                ),
            ),
        ),
    ),
)


def _start_mission(events: OutputEvents, mission: Mission) -> None:
    events.robot.request(lambda a: a.execute_mission, mission)
    events.mqtt.publish_mission_status(mission.id, MissionStatus.InProgress, None)


def _start_mission_and_respond(events: OutputEvents, mission: Mission) -> None:
    _start_mission(events, mission)
    events.api.respond(
        lambda r: r.start_mission, MissionStartResponse(mission_started=True)
    )


transition_and_start_mission: TransitionDef[Mission, str] = TransitionDef(
    state, lambda mission: mission.id, side_effect=_start_mission
)
transition_and_start_mission_and_respond_to_api: TransitionDef[Mission, str] = (
    TransitionDef(
        state, lambda mission: mission.id, side_effect=_start_mission_and_respond
    )
)
transition_with_existing_mission: TransitionDef[str, str] = TransitionDef(
    state, forward
)
