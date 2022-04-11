from isar.models.mission import Mission
from tests.mocks.task import MockTask


class MockMissionDefinition:
    default_mission = Mission(
        id="default_mission",
        tasks=[
            MockTask.take_image_in_coordinate_direction,
            MockTask.drive_to,
            MockTask.take_image_in_coordinate_direction,
            MockTask.take_image_in_coordinate_direction,
        ],
    )
