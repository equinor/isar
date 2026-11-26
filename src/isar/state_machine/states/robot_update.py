import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
from isar.state_machine.output_events import OutputEvent
from isar.state_machine.state import (
    Branch,
    EventHandler,
    StateDef,
    TransitionDef,
    TransitionEffect,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.polygon import Polygon

state: StateDef[None] = StateDef(
    name=States.RobotUpdate,
    handlers=lambda: (
        EventHandler(
            event=lambda e: e.action_requests.update_exclusion_polygons.success,
            branches=(Branch(Home.transition),),
        ),
        EventHandler(
            event=lambda e: e.action_requests.update_exclusion_polygons.failure,
            branches=(
                Branch(
                    InterventionNeeded.transition,
                    lambda _, __: "Failed to update exclusion polygons",
                ),
            ),
        ),
    ),
)

_request_update_exclusion_polygons: TransitionEffect[list[Polygon]] = TransitionEffect(
    OutputEvent.robot_request(lambda a: a.update_exclusion_polygons),
    lambda polygons: polygons,
)

transition_and_update_exclusion_polygons: TransitionDef[list[Polygon], None] = (
    TransitionDef(
        state,
        side_effects=(_request_update_exclusion_polygons,),
    )
)
