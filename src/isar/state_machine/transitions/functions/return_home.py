from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine

from typing import TYPE_CHECKING

from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import ReturnToHome

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def start_return_home_mission(state_machine: "StateMachine") -> bool:
    state_machine.start_mission(
        Mission(
            tasks=[ReturnToHome()],
            name="Return Home",
        )
    )
    return True
