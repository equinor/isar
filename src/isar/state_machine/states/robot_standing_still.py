from typing import TYPE_CHECKING

from transitions import State

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from isar.state_machine.generic_states.idle import Idle, IdleStates


class RobotStandingStill(State, Idle):
    def __init__(self, state_machine: "StateMachine") -> None:
        State.__init__(
            self, name="robot_standing_still", on_enter=self.start, on_exit=self.stop
        )
        Idle.__init__(
            self,
            state_machine=state_machine,
            state=IdleStates.RobotStandingStill,
        )
