import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.maintenance as Maintenance
from isar.apis.models.models import MaintenanceResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.services.utilities.mqtt_utilities import publish_mission_aborted
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States


def StoppingDueToMaintenance(events: Events, mission_id: str | None = None) -> State:

    def _failed_stop_event_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.set_maintenance_mode.response.trigger_event(
            MaintenanceResponse(
                is_maintenance_mode=False,
                failure_reason="Failed to stop ongoing mission",
            )
        )
        return InterventionNeeded.transition(
            "Failed to stop mission when entering maintenance mode"
        )

    def _successful_stop_event_handler(
        _: AbortedMission | EmptyMessage,
    ) -> Transition:
        if mission_id:
            publish_mission_aborted(
                events.mqtt_queue,
                mission_id,
                "Mission aborted, robot being sent to maintenance",
            )
        return Maintenance.transition_and_reply_to_API()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.mission_failed_to_stop,
            handler=_failed_stop_event_handler,
        ),
        EventHandlerMapping[AbortedMission](
            event=events.robot_service_events.mission_successfully_stopped,
            handler=_successful_stop_event_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.robot_service_events.stopped_mission_already_done,
            handler=_successful_stop_event_handler,
        ),
    ]
    return State(
        state_name=States.StoppingDueToMaintenance,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_stop_mission(
    mission_id: str | None = None,
) -> Transition:
    def _transition(events: Events) -> State:
        events.state_machine_events.stop_mission.trigger_event(EmptyMessage())
        return StoppingDueToMaintenance(events, mission_id)

    return _transition
