from dataclasses import dataclass
from typing import Optional

from alitra import Pose

from isar.models.mission import Mission


@dataclass
class StartMissionMessage:
    mission: Mission
    initial_pose: Optional[Pose]
