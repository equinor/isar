def test_no_transitions_to_non_states(states_graph: dict[str, list[str]]) -> None:
    all_states = set(states_graph.keys())
    for state_name, transitions in states_graph.items():
        for transition in transitions:
            assert (
                transition in all_states
            ), f"State {state_name} transitions to invalid state {transition}"


def test_no_unreachable_states(states_graph: dict[str, list[str]]) -> None:
    all_states = set(states_graph.keys())
    for transitions in states_graph.values():
        for transition in transitions:
            all_states.discard(transition)
    assert (
        len(all_states) == 0
    ), f"States {",".join(all_states)} are never transitioned to"


def test_no_dead_end_states(states_graph: dict[str, list[str]]) -> None:
    for state_name, transitions in states_graph.items():
        assert len(transitions) > 0, f"State {state_name} has no transitions"


def _find_all_linked_states(
    graph: dict[str, list[str]], current_state: str, already_seen_states: set[str]
) -> set[str]:
    for transition in graph[current_state]:
        if transition in already_seen_states:
            continue
        already_seen_states.add(transition)
        already_seen_states = _find_all_linked_states(
            graph, transition, already_seen_states
        )

    return already_seen_states


def test_no_closed_loops(states_graph: dict[str, list[str]]) -> None:
    for state_name in states_graph:
        all_linked_states = _find_all_linked_states(states_graph, state_name, set())
        assert len(all_linked_states.intersection(set(states_graph.keys()))) == len(
            states_graph
        ), f"State {state_name} cannot reach all other states"
