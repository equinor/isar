import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_lockdown_with_mission as GoingToLockdownWithMission
import isar.state_machine.states.monitor as Monitor
from isar.apis.models.models import LockdownResponse
from isar.models.events import AbortedMission, EmptyMessage, Events, MissionCompleted
from isar.state_machine.state import EventHandlerMapping, StateDef, Transition
from isar.state_machine.states_enum import States


def StoppingGoToLockdown(events: Events, mission_id: str) -> StateDef:

    def _failed_stop_event_handler(
        _: EmptyMessage,
    ) -> Transition:
        events.api_requests.send_to_lockdown.trigger_response(
            LockdownResponse(
                lockdown_started=False,
                failure_reason="Failed to stop ongoing mission",
            )
        )
        return Monitor.transition_with_existing_mission(mission_id)

    def _successful_stop_event_handler(
        mission: AbortedMission | MissionCompleted | EmptyMessage,
    ) -> Transition:
        if isinstance(mission, AbortedMission):
            return GoingToLockdownWithMission.transition_and_start_mission_and_report_to_api(
                mission
            )
        else:
            return GoingToLockdown.transition_and_start_mission_and_report_to_api()

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=_failed_stop_event_handler,
        ),
        EventHandlerMapping[AbortedMission | MissionCompleted | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=_successful_stop_event_handler,
        ),
    ]
    return StateDef(
        name=States.StoppingGoToLockdown,
        handlers=event_handlers,
    )


def transition_and_stop_mission(mission_id: str) -> Transition:
    def _transition(events: Events) -> StateDef:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        return StoppingGoToLockdown(events, mission_id)

    return _transition
