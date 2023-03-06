from dataclasses import dataclass
from typing import Optional

from alitra import Pose

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.mission.mission import Mission


@dataclass
class StartMissionMessage:
    mission: Mission
    mission_metadata: MissionMetadata
    initial_pose: Optional[Pose]
