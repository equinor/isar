import os
from pathlib import Path
from injector import Injector
from transitions.extensions import GraphMachine

from isar.modules import get_injector
from isar.state_machine.state_machine import StateMachine

if __name__ == "__main__":
    injector: Injector = get_injector()
    state_machine: StateMachine = injector.get(StateMachine)
    machine = GraphMachine(states=state_machine.states, initial="off", queued=True)
    machine.add_transitions(state_machine.transitions)
    gp = machine.get_combined_graph()

    state_machine_diagram_file = (
        Path(__file__).parent.resolve().joinpath(Path("state_machine_diagram.png"))
    )

    os.remove(state_machine_diagram_file)

    gp.draw(state_machine_diagram_file, prog="dot")
