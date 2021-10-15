import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from isar.config import config
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.models.mission import Mission
from isar.services.readers.base_reader import BaseReader, BaseReaderError
from robot_interface.models.geometry.frame import Frame

logger = logging.getLogger("api")


class LocalPlanner(MissionPlannerInterface):
    def __init__(
        self,
        predefined_mission_folder: Path = Path(
            config.get("mission", "eqrobot_pre_defined_missions_folder")
        ),
    ):
        self.predefined_mission_folder = predefined_mission_folder

    def get_mission(self, mission_id) -> Mission:
        missions: dict = self.get_predefined_missions()
        if missions is None:
            raise MissionPlannerError("There were no predefined missions")
        try:
            return missions[mission_id]["mission"]
        except Exception as e:
            raise MissionPlannerError(
                f"Could not get mission : {mission_id} - does not exist {e}"
            ) from e

    @staticmethod
    def read_mission_from_file(mission_path: Path) -> Optional[Mission]:
        mission_dict: dict = BaseReader.read_json(location=mission_path)
        mission: Mission = BaseReader.dict_to_dataclass(
            dataclass_dict=mission_dict,
            target_dataclass=Mission,
            cast_config=[Frame],
            strict_config=True,
        )

        return mission

    def get_predefined_missions(self) -> dict:
        missions: dict = {}
        invalid_mission_ids: list = []
        json_files = self.predefined_mission_folder.glob("*.json")
        for file in json_files:
            mission_name = file.stem
            path_to_file = self.predefined_mission_folder.joinpath(file.name)
            try:

                mission: Mission = self.read_mission_from_file(path_to_file)
            except BaseReaderError as e:
                logger.warning(
                    f"Failed to read predefined mission {path_to_file} \n {e}"
                )
                continue
            if mission.mission_id in invalid_mission_ids:
                logger.warning(
                    f"Duplicate mission_id {mission.mission_id} : {path_to_file.as_posix()}"
                )
            elif mission.mission_id in missions:
                conflicting_file_path = missions[mission.mission_id]["file"]
                logger.warning(
                    f"Duplicate mission_id {mission.mission_id} : {path_to_file.as_posix()}"
                    + f" and {conflicting_file_path}"
                )
                invalid_mission_ids.append(mission.mission_id)
                missions.pop(mission.mission_id)
            else:
                missions[mission.mission_id] = {
                    "name": mission_name,
                    "file": path_to_file.as_posix(),
                    "mission": mission,
                }
        return missions

    def list_predefined_missions(self) -> Optional[dict]:
        mission_list_dict = self.get_predefined_missions()
        predefined_mission_list = []
        for mission_id, current_mission in mission_list_dict.items():
            predefined_mission_list.append(
                {
                    "id": mission_id,
                    "name": current_mission["name"],
                    "file": current_mission["file"],
                    "mission_steps": asdict(current_mission["mission"])[
                        "mission_steps"
                    ],
                }
            )
        return {"missions": predefined_mission_list}

    def mission_id_valid(self, mission_id: int) -> bool:
        mission_list_dict = self.get_predefined_missions()
        if mission_id in mission_list_dict:
            return True
        else:
            logger.error(f"Mission ID: {mission_id} does not exist")
            return False
