import pytest
from requests import RequestException

from isar.mission_planner.echo_planner import EchoPlanner
from isar.models.mission import Mission
from isar.services.service_connections.stid.stid_service import StidService
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.position import Position
from robot_interface.models.mission import DriveToPose, TakeImage, TakeThermalImage


@pytest.mark.parametrize(
    "id, mock_return, mock_stid_side_effect, mock_stid, expected_return",
    [
        (
            76,
            {
                "robotPlanId": 76,
                "planItems": [
                    {
                        "planItemId": 1227,
                        "tag": "313-PA-101A",
                        "sortingOrder": 0,
                        "robotPlanId": 76,
                    },
                ],
            },
            None,
            Position(x=1, y=1, z=0, frame=Frame.Asset),
            {
                "mission_tasks": 3,
                "mission_task_1_type": DriveToPose,
                "mission_task_2_type": TakeThermalImage,
            },
        ),
        (
            76,
            {
                "robotPlanId": 76,
                "planItems": [
                    {
                        "planItemId": 1227,
                        "tag": "314-LD-1001",
                        "sortingOrder": 0,
                        "robotPlanId": 76,
                    },
                ],
            },
            None,
            Position(x=1, y=1, z=0, frame=Frame.Asset),
            {
                "mission_tasks": 2,
                "mission_task_1_type": DriveToPose,
                "mission_task_2_type": TakeImage,
            },
        ),
        (
            76,
            {
                "robotPlanId": 76,
                "planItems": [
                    {
                        "planItemId": 1227,
                        "tag": "wrong_tag",
                        "sortingOrder": 0,
                        "robotPlanId": 76,
                    },
                ],
            },
            RequestException,
            Position(x=1, y=1, z=0, frame=Frame.Asset),
            {
                "mission_tasks": 0,
                "mission_task_1_type": None,
                "mission_task_2_type": None,
            },
        ),
    ],
)
def test_get_echo_mission(
    echo_service,
    mocker,
    id,
    mock_return,
    mock_stid_side_effect,
    mock_stid,
    expected_return,
):
    mocker.patch.object(EchoPlanner, "_mission_plan", return_value=mock_return)
    mocker.patch.object(
        StidService,
        "tag_position",
        return_value=mock_stid,
        side_effect=mock_stid_side_effect,
    )
    mission: Mission = echo_service.get_mission(mission_id=id)
    assert len(mission.mission_tasks) == expected_return["mission_tasks"]
    if not len(mission.mission_tasks) == 0:
        assert isinstance(
            mission.mission_tasks[0], expected_return["mission_task_1_type"]
        )
        assert isinstance(
            mission.mission_tasks[1], expected_return["mission_task_2_type"]
        )
