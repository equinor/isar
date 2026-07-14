from typing import TYPE_CHECKING, List

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.pausing as Pausing
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_lockdown as StoppingGoToLockdown
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
from isar.apis.models.models import ControlMissionResponse, MissionStartResponse
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import EmptyMessage
from isar.services.utilities.mqtt_utilities import publish_mission_status
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):

    def __init__(self, state_machine: "StateMachine", mission_id: str):
        events = state_machine.events

        def _mission_success_event_handler(
            success: EmptyMessage,
        ) -> Transition[AwaitNextMission.AwaitNextMission]:
            state_machine.logger.info("Mission succeeded")
            publish_mission_status(
                state_machine.mqtt_publisher, mission_id, MissionStatus.Successful, None
            )
            return AwaitNextMission.transition()

        def _mission_failed_event_handler(
            error_message: ErrorMessage,
        ) -> Transition[AwaitNextMission.AwaitNextMission]:
            state_machine.logger.warning(
                f"Mission failed because: " f"{error_message.error_description}"
            )
            publish_mission_status(
                state_machine.mqtt_publisher,
                mission_id,
                MissionStatus.Failed,
                error_message,
            )
            return AwaitNextMission.transition()

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Transition[Stopping.Stopping] | None:
            if mission_id == stop_mission_id or stop_mission_id == "":
                return Stopping.transition_and_trigger_stop(mission_id, True)
            else:
                state_machine.events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(
                        success=False, failure_reason="Mission not found"
                    )
                )
                return None

        def _mission_started_event_handler(mission_started: EmptyMessage) -> None:
            publish_mission_status(
                state_machine.mqtt_publisher, mission_id, MissionStatus.InProgress, None
            )

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                name="mission_started_event",
                event=events.robot_service_events.mission_started_successfully,
                handler=_mission_started_event_handler,
            ),
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="pause_mission_event",
                event=events.api_requests.pause_mission.request,
                handler=lambda _: Pausing.transition_and_pause_mission_and_reply_to_API(
                    mission_id
                ),
            ),
            EventHandlerMapping[ErrorMessage](
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="mission_succeeded_event",
                event=events.robot_service_events.mission_succeeded,
                handler=_mission_success_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="robot_battery_below_threshold_event",
                event=events.robot_service_events.battery_below_mission_threshold,
                handler=lambda _: StoppingGoToRecharge.transition_and_stop_mission(),
            ),
            EventHandlerMapping[EmptyMessage](
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: StoppingGoToLockdown.transition_and_stop_mission(
                    mission_id
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(
                    mission_id
                ),
            ),
        ]
        super().__init__(
            state_name=States.Monitor,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition_and_start_mission(
    mission: Mission, should_respond_to_API_request: bool = False
) -> Transition[Monitor]:
    def _transition(state_machine: "StateMachine") -> Monitor:
        publish_mission_status(
            state_machine.mqtt_publisher, mission.id, MissionStatus.NotStarted, None
        )
        if state_machine.events.robot_service_events.mission_failed.clear_event():
            state_machine.logger.warning("Mission failed had lingering event")
        if state_machine.events.robot_service_events.mission_succeeded.clear_event():
            state_machine.logger.warning("Mission succeeded had lingering event")
        if (
            state_machine.events.robot_service_events.mission_started_successfully.clear_event()
        ):
            state_machine.logger.warning("Mission started had lingering event")
        state_machine.start_mission(mission=mission)
        if should_respond_to_API_request:
            state_machine.events.api_requests.start_mission.response.trigger_event(
                MissionStartResponse(mission_started=True)
            )
        return Monitor(state_machine, mission_id=mission.id)

    return _transition


def transition_with_existing_mission(mission_id: str) -> Transition[Monitor]:
    def _transition(state_machine: "StateMachine") -> Monitor:
        return Monitor(state_machine, mission_id=mission_id)

    return _transition
