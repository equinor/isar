from typing import TYPE_CHECKING

from transitions import State

from isar.state_machine.generic_states.ongoing_mission import (
    OngoingMission,
    OngoingMissionStates,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State, OngoingMission):
    def __init__(self, state_machine: "StateMachine") -> None:
        State.__init__(self, name="monitor", on_enter=self.start, on_exit=self.stop)

        OngoingMission.__init__(
            self,
            state_machine=state_machine,
            state=OngoingMissionStates.Monitor,
        )
