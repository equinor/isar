import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.resuming_return_home as ResumingReturnHome
import isar.state_machine.states.returning_home as ReturningHome
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_paused_return_home as StoppingPausedReturnHome
from isar.models.events import EmptyMessage
from isar.state_machine.capabilities import OutputEvents
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    forward,
    forward_event,
)
from isar.state_machine.states_enum import States


def _request_resume(events: OutputEvents, _: None, __: EmptyMessage) -> None:
    events.robot.request(lambda a: a.resume_mission, EmptyMessage())


state: StateDef[None] = StateDef(
    name=States.ReturnHomePaused,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.api_requests.resume_mission.request,
            branches=(
                Branch(
                    ResumingReturnHome.transition_and_resume_return_home_and_respond_to_api
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.robot_async_events.battery_below_mission_threshold,
            branches=(Branch(ReturningHome.transition_with_existing_mission),),
        ),
        EventHandler(
            event=lambda e: e.api_requests.start_mission.request,
            branches=(
                Branch(
                    StoppingPausedReturnHome.transition_and_stop_return_home_and_respond_to_api,
                    forward_event,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.send_to_lockdown.request,
            branches=(
                Branch(
                    GoingToLockdown.transition_with_existing_mission_and_respond_to_api,
                    side_effect=_request_resume,
                ),
            ),
        ),
        EventHandler(
            event=lambda e: e.api_requests.set_maintenance_mode.request,
            branches=(Branch(StoppingDueToMaintenance.transition_and_stop_mission),),
        ),
    ),
)

transition: TransitionDef[None, None] = TransitionDef(state, forward)
