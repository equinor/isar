import os
from pathlib import Path
from typing import List

from injector import Injector
from transitions import State
from transitions.extensions import GraphMachine

from isar.modules import get_injector
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.transitions.mission import get_mission_transitions
from isar.state_machine.transitions.return_home import get_return_home_transitions
from isar.state_machine.transitions.robot_status import get_robot_status_transitions


def draw_diagram(states: List[State], transitions: List[dict], name: str):
    machine = GraphMachine(states=states, initial="unknown_status", queued=True)
    machine.add_transitions(transitions)
    gp = machine.get_combined_graph()

    state_machine_diagram_file = (
        Path(__file__).parent.resolve().joinpath(Path(f"{name}.png"))
    )

    if os.path.isfile(state_machine_diagram_file):
        os.remove(state_machine_diagram_file)

    gp.draw(state_machine_diagram_file, prog="dot")


if __name__ == "__main__":
    injector: Injector = get_injector()
    state_machine: StateMachine = injector.get(StateMachine)

    mission_extended_transitions: List[dict] = []
    for transition in get_mission_transitions(state_machine):
        mission_extended_transitions.append(transition)

    for transition in get_return_home_transitions(state_machine):
        mission_extended_transitions.append(transition)

    draw_diagram(
        states=state_machine.states,
        transitions=mission_extended_transitions,
        name="mission_state_machine_diagram",
    )

    draw_diagram(
        states=state_machine.states,
        transitions=get_robot_status_transitions(state_machine),
        name="robot_status_state_machine_diagram",
    )

    draw_diagram(
        states=state_machine.states,
        transitions=state_machine.transitions,
        name="full_state_machine_diagram",
    )
