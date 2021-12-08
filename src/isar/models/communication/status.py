from dataclasses import dataclass
from typing import Optional

from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission import Task, TaskStatus


@dataclass
class Status:
    mission_in_progress: bool
    current_task: Optional[Task]
    current_mission: Mission
    current_state: States
