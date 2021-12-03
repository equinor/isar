from typing import Literal

from isar.models.mission import Mission
from tests.mocks.task import MockTask

default_mission = Mission(
    id="default_mission",
    tasks=[
        MockTask.take_image_in_coordinate_direction(),
        MockTask.drive_to(),
        MockTask.take_image_in_coordinate_direction(),
        MockTask.take_image_in_coordinate_direction(),
    ],
)

long_mission = Mission(
    id="long_mission",
    tasks=[
        MockTask.take_image_in_coordinate_direction(),
        MockTask.take_image_in_coordinate_direction(),
        MockTask.drive_to(),
        MockTask.drive_to(),
        MockTask.take_image_in_coordinate_direction(),
        MockTask.take_image_in_coordinate_direction(),
    ],
)


empty_mission = Mission(id=None, tasks=[])


mission_name_typehints = Literal["default_mission", "empty_mission", "long_mission"]


def mock_mission_definition(
    mission_name: mission_name_typehints = "default_mission",
) -> Mission:
    if mission_name == "default_mission":
        return default_mission
    elif mission_name == "empty_mission":
        return empty_mission
    elif mission_name == "long_mission":
        return long_mission
