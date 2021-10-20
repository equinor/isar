from datetime import datetime

import pytest

from isar.state_machine.states_enum import States
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.inspection.inspection import Inspection, TimeIndexedPose
from robot_interface.models.inspection.metadata import ImageMetadata
from robot_interface.models.inspection.references import ImageReference
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
@pytest.mark.unittest
def test_collect_results(
    collect,
    mocker,
    current_mission_step,
    mock_collect_results,
    expected_state,
):
    collect.state_machine.current_mission_step = current_mission_step
    mocker.patch.object(
        MockRobot,
        "get_inspection_references",
        return_value=mock_collect_results,
    )
    next_state = collect._collect_results()
    assert next_state is expected_state
