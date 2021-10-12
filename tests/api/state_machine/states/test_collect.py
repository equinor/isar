from datetime import datetime

import pytest

from models.enums.states import States
from models.geometry.frame import Frame
from models.geometry.orientation import Orientation
from models.geometry.pose import Pose
from models.geometry.position import Position
from models.inspections.inspection import Inspection
from models.inspections.references.image_reference import ImageReference
from models.metadata.inspection_metadata import TimeIndexedPose
from models.metadata.inspections.image_metadata import ImageMetadata
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot
from tests.test_utilities.mock_models.mock_step import MockStep


def mock_inspection() -> Inspection:
    return ImageReference(
        id="some-inspection-id",
        metadata=ImageMetadata(
            datetime.now(),
            TimeIndexedPose(
                Pose(
                    Position(0, 0, 0, Frame.Robot),
                    Orientation(0, 0, 0, 1, Frame.Robot),
                    Frame.Robot,
                ),
                datetime.now(),
            ),
            file_type="jpg",
        ),
    )


@pytest.mark.parametrize(
    "current_mission_step, mock_collect_results, expected_state",
    [
        (
            MockStep.take_image_in_coordinate_direction(),
            [mock_inspection()],
            States.Send,
        ),
        (MockStep.take_image_in_coordinate_direction(), [], States.Send),
    ],
)
def test_collect_results(
    collect,
    mocker,
    current_mission_step,
    mock_collect_results,
    expected_state,
):
    collect.state_machine.status.current_mission_step = current_mission_step
    mocker.patch.object(
        MockRobot,
        "get_inspection_references",
        return_value=mock_collect_results,
    )
    next_state = collect.collect_results()
    assert next_state is expected_state
