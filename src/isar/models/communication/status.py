from dataclasses import dataclass
from typing import Optional

from isar.models.mission import Mission
from models.enums.mission_status import MissionStatus
from models.enums.states import States
from models.planning.step import Step


@dataclass
class Status:
    mission_status: Optional[MissionStatus]
    mission_in_progress: bool
    current_mission_instance_id: Optional[int]
    current_mission_step: Optional[Step]
    mission_schedule: Mission
    current_state: States
