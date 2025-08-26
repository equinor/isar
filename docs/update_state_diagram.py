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


def extract_condition_name_from_lambda(cond):

    try:
        closure = cond.__closure__
        if closure:
            for cell in closure:
                obj = cell.cell_contents
                if callable(obj) and hasattr(obj, "__name__"):
                    return obj.__name__
        return "lambda"
    except Exception:
        return "unknown"


def embed_conditions_in_trigger(transitions: List[dict]) -> List[dict]:
    updated = []
    for t in transitions:
        trigger = t.get("trigger", "")
        conditions = t.get("conditions", [])

        if not isinstance(conditions, list):
            conditions = [conditions]

        condition_names = []

        for cond in conditions:
            name = extract_condition_name_from_lambda(cond)
            condition_names.append(name)

        condition_str = ", ".join(condition_names)
        new_trigger = f"{trigger} [{condition_str}]" if condition_names else trigger

        t_copy = t.copy()
        t_copy["trigger"] = new_trigger
        updated.append(t_copy)

    return updated


def draw_diagram(states: List[State], transitions: List[dict], name: str):
    transitions_with_conditions = embed_conditions_in_trigger(transitions)
    machine = GraphMachine(states=states, initial="unknown_status", queued=True)
    machine.add_transitions(transitions_with_conditions)
    gp = machine.get_combined_graph()

    state_machine_diagram_file = (
        Path(__file__).parent.resolve().joinpath(Path(f"{name}.png"))
    )

    if os.path.isfile(state_machine_diagram_file):
        os.remove(state_machine_diagram_file)

    gp.draw(str(state_machine_diagram_file), prog="dot", format="png")


if __name__ == "__main__":
    injector: Injector = get_injector()
    state_machine: StateMachine = injector.state_machine()

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
