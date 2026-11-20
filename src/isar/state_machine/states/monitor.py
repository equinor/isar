import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.pausing as Pausing
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
from isar.apis.models.models import MissionStartResponse
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
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus

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
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            lambda mission_id, error: MissionStatusUpdate(
                                mission_id, MissionStatus.Failed, error
                            ),
                        ),
                    ),
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.action_requests.execute_mission.success,
            branches=(
                Branch(
                    AwaitNextMission.transition,
                    effects=(
                        HandlerEffect(
                            lambda e: e.mqtt_queue.publish_mission_result,
                            lambda mission_id, _: MissionStatusUpdate(
                                mission_id, MissionStatus.Successful
                            ),
                        ),
                    ),
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


_request_execute_mission: TransitionEffect[Mission] = TransitionEffect(
    lambda e: e.action_requests.execute_mission.trigger_request,
    lambda mission: mission,
)
_publish_in_progress: TransitionEffect[Mission] = TransitionEffect(
    lambda e: e.mqtt_queue.publish_mission_progress,
    lambda mission: MissionStatusUpdate(mission.id, MissionStatus.InProgress),
)

transition_and_start_mission: TransitionDef[Mission, str] = TransitionDef(
    state,
    lambda mission: mission.id,
    effects=(_request_execute_mission, _publish_in_progress),
)
transition_and_start_mission_and_respond_to_api: TransitionDef[Mission, str] = (
    TransitionDef(
        state,
        lambda mission: mission.id,
        effects=(
            _request_execute_mission,
            _publish_in_progress,
            TransitionEffect(
                lambda e: e.api_requests.start_mission.trigger_response,
                lambda _: MissionStartResponse(mission_started=True),
            ),
        ),
    )
)
transition_with_existing_mission: TransitionDef[str, str] = TransitionDef(
    state, forward_transition_parameter
)
