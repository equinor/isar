import json
import logging
from pathlib import Path

from dependency_injector.wiring import inject

from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import (
    MissionNotFoundError,
    MissionPlannerError,
    MissionPlannerInterface,
)
from robot_interface.models.mission.mission import Mission

logger = logging.getLogger("api")


class LocalPlanner(MissionPlannerInterface):
    @inject
    def __init__(self):
        self.predefined_mission_folder = Path(settings.PREDEFINED_MISSIONS_FOLDER)

    def get_mission(self, mission_id) -> Mission:
        missions: dict = self.get_predefined_missions()
        if missions is None:
            raise MissionPlannerError("There were no predefined missions")
        try:
            mission: Mission = missions[mission_id]["mission"]
            return mission
        except KeyError as e:
            raise MissionNotFoundError(
                f"Could not get mission : {mission_id} - does not exist {e}"
            ) from e
        except Exception as e:
            raise MissionPlannerError(f"Could not get mission : {mission_id}") from e

    @staticmethod
    def read_mission_from_file(mission_path: Path) -> Mission:
        with open(mission_path) as json_file:
            mission_dict = json.load(json_file)

        return Mission(**mission_dict)

    def get_predefined_missions(self) -> dict:
        missions: dict = {}
        invalid_mission_ids: list = []
        json_files = self.predefined_mission_folder.glob("*.json")
        for file in json_files:
            mission_name = file.stem
            path_to_file = self.predefined_mission_folder.joinpath(file.name)

            mission: Mission = self.read_mission_from_file(path_to_file)
            if mission.id in invalid_mission_ids:
                logger.warning(
                    f"Duplicate mission id {mission.id} : {path_to_file.as_posix()}"
                )
            elif mission.id in missions:
                conflicting_file_path = missions[mission.id]["file"]
                logger.warning(
                    f"Duplicate mission id {mission.id} : {path_to_file.as_posix()}"
                    + f" and {conflicting_file_path}"
                )
                invalid_mission_ids.append(mission.id)
                missions.pop(mission.id)
            else:
                missions[mission.id] = {
                    "name": mission_name,
                    "file": path_to_file.as_posix(),
                    "mission": mission,
                }
        return missions
