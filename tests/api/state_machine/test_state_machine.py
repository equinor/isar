from pathlib import Path

import pytest

from isar.models.mission import Mission
from isar.services.readers.mission_reader import MissionReader
from models.enums.states import States


def get_mission():
    mission_reader: MissionReader = MissionReader()
    mission: Mission = mission_reader.get_mission(
        Path("./tests/test_data/test_mission_working.json")
    )
    return mission


class TestStateMachine:
    def test_initial_off(self, state_machine):
        assert state_machine.state == "off"

    @pytest.mark.parametrize(
        "should_send, expected_output", [(True, True), (False, False)]
    )
    def test_should_send_status(self, state_machine, should_send, expected_output):
        if should_send is not None:
            state_machine.queues.mission_status.input.put(should_send)
        send: bool = state_machine.should_send_status()

        assert send is expected_output

    def test_send_status(self, state_machine):
        state_machine.send_status()
        message = state_machine.queues.mission_status.output.get()
        assert message

    def test_reset_state_machine(self, state_machine):
        next_state = state_machine.reset_state_machine()

        assert not state_machine.status.mission_in_progress
        assert state_machine.status.current_mission_instance_id is None
        assert state_machine.status.current_mission_step is None
        assert state_machine.status.mission_schedule.mission_steps == []
        assert next_state is States.Idle

    @pytest.mark.parametrize(
        "mission, mission_in_progress, expected_output",
        [
            (None, True, (False, None)),
            (Mission([], None), True, (False, None)),
            (Mission([], None), False, (True, Mission([], None))),
        ],
    )
    def test_should_start_mission(
        self, state_machine, mission, mission_in_progress, expected_output
    ):
        state_machine.queues.start_mission.input.put(mission)
        state_machine.status.mission_in_progress = mission_in_progress
        output = state_machine.should_start_mission()

        assert output == expected_output

    def test_start_mission(self, state_machine):
        state_machine.start_mission(1)
        message = state_machine.queues.start_mission.output.get()
        assert state_machine.status.mission_in_progress
        assert message

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
        if should_stop is not None:
            state_machine.queues.stop_mission.input.put(should_stop)
        state_machine.status.mission_in_progress = mission_in_progress
        start: bool = state_machine.should_stop()

        assert start is expected_output

    def test_stop_mission(self, state_machine):
        state_machine.stop_mission()
        message = state_machine.queues.stop_mission.output.get()
        assert not state_machine.status.mission_in_progress
        assert message
