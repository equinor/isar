from dataclasses import dataclass
from typing import Optional

from alitra import Pose

from robot_interface.models.mission.mission import Mission


@dataclass
class StartMissionMessage:
    mission: Mission
    initial_pose: Optional[Pose]
