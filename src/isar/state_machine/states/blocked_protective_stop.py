from typing import TYPE_CHECKING

from transitions import State

from isar.state_machine.generic_states.robot_unavailable import (
    RobotUnavailable,
    RobotUnavailableStates,
)

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class BlockedProtectiveStop(State, RobotUnavailable):
    def __init__(self, state_machine: "StateMachine") -> None:
        State.__init__(
            self, name="blocked_protective_stop", on_enter=self.start, on_exit=self.stop
        )

        RobotUnavailable.__init__(
            self,
            state_machine=state_machine,
            state=RobotUnavailableStates.BlockedProtectiveStop,
        )
