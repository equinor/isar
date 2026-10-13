import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import MissionStartResponse, TeleoperationResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


def Teleoperation(events: Events) -> State:

    def _start_mission_request_handler(mission: Mission) -> None:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        response: AbortedMission | EmptyMessage | None = None
        success: bool = False
        while not response:
            response = events.action_requests.stop_mission.failure.consume_event()
            if response is None:
                response = events.action_requests.stop_mission.success.consume_event()
                success = True

        if not success:
            events.api_requests.start_mission.trigger_response(
                MissionStartResponse(
                    mission_started=False,
                    mission_not_started_reason="Failed to stop ongoing mission",
                )
            )

        events.action_requests.execute_mission.trigger_request(mission)

        events.api_requests.start_mission.trigger_response(
            MissionStartResponse(mission_started=True)
        )

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.return_home.request,
            handler=lambda _: ReturningHome.transition_and_start_mission(True),
        ),
        EventHandlerMapping[Mission](
            event=events.api_requests.start_mission.request,
            handler=_start_mission_request_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: Maintenance.transition_and_reply_to_API(),
        ),
    ]

    return State(
        state_name=States.Teleoperation,
        signal_exit_event=events.signal_state_machine_exit,
        event_handler_mappings=event_handlers,
    )


def transition_and_reply_to_API() -> Transition:
    def _transition(events: Events) -> State:
        events.api_requests.set_teleoperation_mode.trigger_response(
            TeleoperationResponse(is_teleoperation_mode=True)
        )
        return Teleoperation(events)

    return _transition
