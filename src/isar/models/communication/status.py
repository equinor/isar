from dataclasses import dataclass
from typing import Optional

from isar.models.mission import Mission
from isar.state_machine.states_enum import States
from robot_interface.models.mission import MissionStatus, Step


@dataclass
class Status:
    mission_status: Optional[MissionStatus]
    mission_in_progress: bool
    current_mission_instance_id: Optional[int]
    current_mission_step: Optional[Step]
    mission_schedule: Mission
    current_state: States
