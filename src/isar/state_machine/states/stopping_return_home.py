import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
from isar.apis.models.models import MissionStartResponse
from isar.models.events import AbortedMission, EmptyMessage, Events, MissionCompleted
from isar.state_machine.state import EventHandlerMapping, StateDef, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


def StoppingReturnHome(events: Events, mission: Mission) -> StateDef:

    event_handlers: list[EventHandlerMapping] = [
        EventHandlerMapping[EmptyMessage](
            event=events.action_requests.stop_mission.failure,
            handler=lambda _: ReturningHome.transition_to_existing_mission(),
        ),
        EventHandlerMapping[AbortedMission | MissionCompleted | EmptyMessage](
            event=events.action_requests.stop_mission.success,
            handler=lambda _: Monitor.transition_and_start_mission(mission, True),
        ),
    ]
    return StateDef(
        name=States.StoppingReturnHome,
        handlers=event_handlers,
    )


def transition_and_stop_return_home_and_reply_to_API(
    mission: Mission,
) -> Transition:
    def _transition(events: Events) -> StateDef:
        events.action_requests.stop_mission.trigger_request(EmptyMessage())
        response = MissionStartResponse(
            mission_id=mission.id,
            mission_started=True,
        )
        events.api_requests.start_mission.trigger_response(response)
        return StoppingReturnHome(events, mission)

    return _transition
