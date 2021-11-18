from typing import Literal

from isar.models.mission import Mission
from tests.mocks.step import MockStep

default_mission = Mission(
    mission_id="default_mission",
    mission_steps=[
        MockStep.take_image_in_coordinate_direction(),
        MockStep.drive_to(),
        MockStep.take_image_in_coordinate_direction(),
        MockStep.take_image_in_coordinate_direction(),
    ],
)

long_mission = Mission(
    mission_id="long_mission",
    mission_steps=[
        MockStep.take_image_in_coordinate_direction(),
        MockStep.take_image_in_coordinate_direction(),
        MockStep.drive_to(),
        MockStep.drive_to(),
        MockStep.take_image_in_coordinate_direction(),
        MockStep.take_image_in_coordinate_direction(),
    ],
)


empty_mission = Mission(mission_id=None, mission_steps=[])


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
