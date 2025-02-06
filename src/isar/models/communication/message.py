from dataclasses import dataclass

from robot_interface.models.mission.mission import Mission


@dataclass
class StartMissionMessage:
    mission: Mission
