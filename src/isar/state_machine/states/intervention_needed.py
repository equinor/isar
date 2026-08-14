import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.unknown_status as UnknownStatus
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


def InterventionNeeded(events: Events) -> State:

    def release_intervention_needed_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.release_intervention_needed.response.trigger_event(
            EmptyMessage()
        )
        return UnknownStatus.transition()

    def _robot_status_event_handler(
        robot_status: RobotStatus,
    ) -> Transition | None:
        if robot_status == RobotStatus.Home:
            return Home.transition()
        return None

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.return_home.request,
            handler=lambda _: ReturningHome.transition_and_start_mission(True),
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.release_intervention_needed.request,
            handler=release_intervention_needed_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: Maintenance.transition_and_reply_to_API(),
        ),
        EventHandlerMapping[RobotStatus](
            event=events.robot_service_events.robot_status_update,
            handler=_robot_status_event_handler,
        ),
    ]
    return State(
        state_name=States.InterventionNeeded,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition(reason: str) -> Transition:
    def _transition(events: Events) -> State:
        events.mqtt_queue.publish_intervention_needed(error_message=reason)

        return InterventionNeeded(events)

    return _transition
