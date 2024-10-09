import logging
from pathlib import Path
from typing import List

from alitra import Frame
from injector import inject

from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import (
    MissionNotFoundError,
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.services.readers.base_reader import BaseReader, BaseReaderError
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    DockingProcedure,
    Localize,
    MoveArm,
    RecordAudio,
    ReturnToHome,
    TakeImage,
    TakeThermalImage,
    TakeThermalVideo,
    TakeVideo,
    Task,
)

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
        mission_dict: dict = BaseReader.read_json(location=mission_path)

        mission_tasks: List[Task] = []
        task_dataclass: Task = None

        for task in mission_dict["tasks"]:
            if task["type"] == "return_to_home":
                task_dataclass = ReturnToHome
            elif task["type"] == "localize":
                task_dataclass = Localize
            elif task["type"] == "move_arm":
                task_dataclass = MoveArm
            elif task["type"] == "take_image":
                task_dataclass = TakeImage
            elif task["type"] == "take_thermal_image":
                task_dataclass = TakeThermalImage
            elif task["type"] == "take_video":
                task_dataclass = TakeVideo
            elif task["type"] == "take_thermal_video":
                task_dataclass = TakeThermalVideo
            elif task["type"] == "record_audio":
                task_dataclass = RecordAudio
            elif task["type"] == "docking_procedure":
                task_dataclass = DockingProcedure

            if task_dataclass:
                task: Task = BaseReader.dict_to_dataclass(
                    dataclass_dict=task,
                    target_dataclass=task_dataclass,
                    cast_config=[Frame],
                    strict_config=True,
                )
                mission_tasks.append(task)

        mission_dict["tasks"] = []
        mission: Mission = BaseReader.dict_to_dataclass(
            dataclass_dict=mission_dict,
            target_dataclass=Mission,
            cast_config=[Frame],
            strict_config=True,
        )

        mission.tasks = mission_tasks

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
