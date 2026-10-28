import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_go_to_recharge as StoppingGoToRecharge
from isar.apis.models.models import MissionStartResponse, TeleoperationResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, StateDef, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


def Teleoperation(events: Events) -> StateDef:

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
            return

        events.action_requests.execute_mission.trigger_request(mission)

        events.api_requests.start_mission.trigger_response(
            MissionStartResponse(mission_started=True)
        )

    def _return_home_request_handler(_: EmptyMessage) -> Transition:
        events.api_requests.return_home.response.trigger_event(EmptyMessage())
        return StoppingGoToRecharge.transition_and_stop_mission()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.return_home.request,
            handler=_return_home_request_handler,
        ),
        EventHandlerMapping[Mission](
            event=events.api_requests.start_mission.request,
            handler=_start_mission_request_handler,
        ),
        EventHandlerMapping[EmptyMessage](
            event=events.api_requests.set_maintenance_mode.request,
            handler=lambda _: StoppingDueToMaintenance.transition_and_stop_mission(),
        ),
    ]

    return StateDef(
        name=States.Teleoperation,
        handlers=event_handlers,
    )


def transition_and_reply_to_API() -> Transition:
    def _transition(events: Events) -> StateDef:
        events.api_requests.set_teleoperation_mode.trigger_response(
            TeleoperationResponse(is_teleoperation_mode=True)
        )
        return Teleoperation(events)

    return _transition
