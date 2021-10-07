from pathlib import Path

import pytest
from isar.mission_planner.local_planner import LocalPlanner
from isar.models.mission import Mission
from isar.state_machine.states_enum import States


def get_mission():
    mission_reader: LocalPlanner = LocalPlanner()
    mission: Mission = mission_reader.read_mission_from_file(
        Path("./tests/test_data/test_mission_working.json")
    )
    return mission


class TestStateMachine:
    def test_initial_off(self, state_machine):
        assert state_machine.state == "off"

    def test_reset_state_machine(self, state_machine):
        next_state = state_machine.reset_state_machine()

        assert not state_machine.mission_in_progress
        assert state_machine.current_mission_instance_id is None
        assert state_machine.current_mission_step is None
        assert state_machine.mission_schedule.mission_steps == []
        assert next_state is States.Idle

    @pytest.mark.parametrize(
        "mission_in_progress, expected_output",
        [
            (True, False),
            (False, True),
        ],
    )
    def test_should_start_mission(
        self, state_machine, mission_in_progress, expected_output
    ):
        state_machine.mission_in_progress = mission_in_progress
        output = state_machine.should_start_mission()

        assert output.started == expected_output

    @pytest.mark.parametrize(
        "should_stop, mission_in_progress, expected_output",
        [
            (True, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, False),
            (None, False, False),
            (None, True, False),
        ],
    )
    def test_should_stop(
        self, state_machine, should_stop, mission_in_progress, expected_output
    ):
        state_machine.stop_flag = should_stop
        state_machine.mission_in_progress = mission_in_progress
        start: bool = state_machine.should_stop()

        assert start is expected_output

    def test_stop_mission(self, state_machine):
        state_machine.stop_mission()
        assert not state_machine.mission_in_progress
