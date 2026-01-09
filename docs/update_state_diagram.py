import ast
import os
from typing import List, Optional

from python_to_mermaid import MermaidDiagram


def get_imports(source_code: str) -> tuple[Optional[str], list]:
    own_class_name = None
    imported_states = []
    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and node.names[0].name.startswith(
            "isar.state_machine.states."
        ):
            state_name = node.names[0].asname
            imported_states.append(state_name)
        if isinstance(node, ast.ClassDef):
            own_class_name = node.name

    return own_class_name, imported_states


def get_all_state_file_paths() -> List[str]:
    cwd = os.getcwd()
    states_folder = os.path.join(cwd, "src", "isar", "state_machine", "states")
    state_files = []
    for file_or_folder in os.listdir(states_folder):
        sub_path = os.path.join(states_folder, file_or_folder)
        if os.path.isfile(sub_path) and not sub_path.endswith("__.py"):
            state_files.append(sub_path)
    return state_files


if __name__ == "__main__":
    state_files = get_all_state_file_paths()

    state_graph = {}

    for state_file in state_files:

        with open(state_file, "r") as file:
            source = file.read()

            own_name, imported_states = get_imports(source)
            state_graph[own_name] = imported_states

    diagram = MermaidDiagram()
    for state in state_graph:
        diagram.add_node(state)

    for state_name, transitions in state_graph.items():
        for transition in transitions:
            diagram.add_edge(state_name, transition)

    mermaid_diagram = str(diagram)

    with open("diagram.mmd", "w") as file:
        file.write(mermaid_diagram)
