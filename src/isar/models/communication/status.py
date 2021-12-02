from dataclasses import dataclass
from typing import Optional

from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission import Task, TaskStatus


@dataclass
class Status:
    task_status: Optional[TaskStatus]
    mission_in_progress: bool
    current_task: Optional[Task]
    mission_schedule: Mission
    current_state: States
