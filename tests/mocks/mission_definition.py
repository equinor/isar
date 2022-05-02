from isar.models.mission import Mission, Task
from tests.mocks.step import MockStep


class MockMissionDefinition:
    default_mission = Mission(
        id="default_mission",
        tasks=[
            Task(
                steps=[MockStep.take_image_in_coordinate_direction, MockStep.drive_to]
            ),
            Task(
                steps=[
                    MockStep.take_image_in_coordinate_direction,
                    MockStep.take_image_in_coordinate_direction,
                ]
            ),
        ],
    )
