from python_to_mermaid import MermaidDiagram

from tests.conftest import (
    get_all_state_file_paths,
    get_state_transitions_from_ast_graph,
)

if __name__ == "__main__":
    state_files = get_all_state_file_paths()

    state_graph = {}

    for state_file in state_files:

        with open(state_file, "r") as file:
            source = file.read()

            own_name, imported_states = get_state_transitions_from_ast_graph(source)
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
