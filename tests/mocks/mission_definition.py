from isar.models.mission import Mission
from tests.mocks.step import MockStep


class MockMissionDefinition:
    default_mission = Mission(
        id="default_mission",
        steps=[
            MockStep.take_image_in_coordinate_direction,
            MockStep.drive_to,
            MockStep.take_image_in_coordinate_direction,
            MockStep.take_image_in_coordinate_direction,
        ],
    )
