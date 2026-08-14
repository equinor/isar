import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.pausing as Pausing
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
from isar.apis.models.models import ControlMissionResponse, MissionStartResponse
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus


def Monitor(events: Events, mission_id: str) -> State:

    def _mission_success_event_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission_id, MissionStatus.Successful, None
        )
        return AwaitNextMission.transition()

    def _mission_failed_event_handler(
        error_message: ErrorMessage,
    ) -> Transition:
        events.mqtt_queue.publish_mission_status(
            mission_id,
            MissionStatus.Failed,
            error_message,
        )
        return AwaitNextMission.transition()

    def _stop_mission_event_handler(
        stop_mission_id: str,
    ) -> Transition | None:
        if mission_id == stop_mission_id or stop_mission_id == "":
            return Stopping.transition_and_trigger_stop_and_respond_to_API(mission_id)
        else:
            events.api_requests.stop_mission.response.trigger_event(
                ControlMissionResponse(
                    success=False, failure_reason="Mission not found"
                )
            )
            return None

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_started_successfully,
            handler=lambda _: events.mqtt_queue.publish_mission_status(
                mission_id, MissionStatus.InProgress, None
            ),
        ),
        EventHandlerMapping[str](
            event=events.api_requests.stop_mission.request,
            handler=_stop_mission_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.pause_mission.request,
            handler=lambda _: Pausing.transition_and_pause_mission_and_reply_to_API(
                mission_id
            ),
        ),
        EventHandlerMapping[ErrorMessage](
            event=events.robot_service_events.mission_failed,
            handler=_mission_failed_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_succeeded,
            handler=_mission_success_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.battery_below_mission_threshold,
            handler=lambda _: StoppingGoToRecharge.transition_and_stop_mission(),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.send_to_lockdown.request,
            handler=lambda _: StoppingGoToLockdown.transition_and_stop_mission(
                mission_id
            ),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(
                mission_id
            ),
        ),
    ]
    return State(
        state_name=States.Monitor,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_start_mission(
    mission: Mission, should_respond_to_API_request: bool = False
) -> Transition:
    def _transition(events: Events) -> State:
        events.mqtt_queue.publish_mission_status(
            mission.id, MissionStatus.NotStarted, None
        )
        events.robot_service_events.mission_failed.clear_event()
        events.robot_service_events.mission_succeeded.clear_event()
        events.robot_service_events.mission_started_successfully.clear_event()

        events.state_machine_events.start_mission.trigger_event(mission)

        if should_respond_to_API_request:
            events.api_requests.start_mission.response.trigger_event(
                MissionStartResponse(mission_started=True)
            )
        return Monitor(events, mission_id=mission.id)

    return _transition


def transition_with_existing_mission(mission_id: str) -> Transition:
    def _transition(events: Events) -> State:
        return Monitor(events, mission_id=mission_id)

    return _transition
