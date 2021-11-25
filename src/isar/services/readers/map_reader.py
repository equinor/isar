import logging
from pathlib import Path
from typing import Optional

from isar.config import config
from isar.models.map.map_config import MapConfig
from isar.services.readers.base_reader import BaseReader
from robot_interface.models.geometry.frame import Frame

logger = logging.getLogger("state_machine")


class MapConfigReader(BaseReader):
    def __init__(
        self,
        predefined_map_config_folder: Path = Path(config.get("DEFAULT", "maps_folder")),
    ):
        self.predefined_map_config_folder = predefined_map_config_folder

    def get_map_config(self, map_config_path: Path) -> Optional[MapConfig]:
        map_config_dict: dict = self.read_json(map_config_path)
        map_config: MapConfig = self.dict_to_dataclass(
            dataclass_dict=map_config_dict,
            target_dataclass=MapConfig,
            cast_config=[Frame],
        )

        return map_config

    def get_predefined_map_configs(self) -> Optional[dict]:
        map_configs: dict = {}
        duplicate_map_config_names: list = []
        json_files = self.predefined_map_config_folder.glob("*.json")
        for file in json_files:
            path_to_file = self.predefined_map_config_folder.joinpath(file.name)
            map_config: MapConfig = self.get_map_config(path_to_file)
            if map_config.map_name in map_configs:
                logger.warning(
                    f"Map name {map_config.map_name} : {path_to_file.as_posix()}"
                    f" already exist. Skipping both original and duplicate ..."
                )
                duplicate_map_config_names.append(map_config.map_name)
            else:
                map_configs[map_config.map_name] = {
                    "name": map_config.map_name,
                    "file": path_to_file.as_posix(),
                    "map_config": map_config,
                }

        for duplicate in duplicate_map_config_names:
            duplicate_map_config = map_configs.pop(duplicate, None)
            logger.warning(
                f"Removing duplicate map name: {duplicate_map_config.map_name}"
            )

        return map_configs

    def get_map_config_by_name(self, map_name) -> Optional[MapConfig]:
        try:
            predefined_map_configs = self.get_predefined_map_configs()
        except Exception as e:
            logger.error(f"Found no map configurations")
            return None

        try:
            return predefined_map_configs[map_name]["map_config"]
        except KeyError as e:
            logger.error(
                f"Could not get map configuration : {map_name} - does not exist {e}"
            )
            return None
