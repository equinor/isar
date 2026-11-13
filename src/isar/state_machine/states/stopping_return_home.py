import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.returning_home as ReturningHome
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
from robot_interface.models.mission.mission import Mission

state: StateDef[Mission] = StateDef(
    name=States.StoppingReturnHome,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.failure,
            branches=(Branch(ReturningHome.transition_with_existing_mission),),
        ),
        EventHandler(
            event=lambda e: e.action_requests.stop_mission.success,
            branches=(
                Branch(Monitor.transition_and_start_mission, forward_state_parameter),
            ),
        ),
    ),
)


def _request_stop_and_respond(events: OutputEvents, mission: Mission) -> None:
    events.robot.request(lambda a: a.stop_mission, EmptyMessage())
    events.api.respond(
        lambda r: r.start_mission,
        MissionStartResponse(mission_id=mission.id, mission_started=True),
    )


transition_and_stop_return_home_and_respond_to_api: TransitionDef[Mission, Mission] = (
    TransitionDef(state, forward, side_effect=_request_stop_and_respond)
)
