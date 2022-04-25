import pytest
from alitra import Frame, Position
from requests import RequestException

from isar.mission_planner.echo_planner import EchoPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.mission import Mission
from isar.services.service_connections.stid.stid_service import StidService
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
                        "sensorTypes": [
                            {"sensorTypeKey": "ThermicPicture"},
                            {"sensorTypeKey": "Picture"},
                        ],
                        "sortingOrder": 0,
                        "robotPlanId": 76,
                    },
                ],
            },
            None,
            Position(x=1, y=1, z=0, frame=Frame("asset")),
            {
                "steps": 3,
                "step_1_type": DriveToPose,
                "step_2_type": TakeThermalImage,
            },
        ),
        (
            76,
            {
                "robotPlanId": 76,
                "planItems": [
                    {
                        "planItemId": 1227,
                        "tag": "355-LD-1003",
                        "sensorTypes": [{"sensorTypeKey": "Picture"}],
                        "sortingOrder": 0,
                        "robotPlanId": 76,
                    },
                ],
            },
            None,
            Position(x=1, y=1, z=0, frame=Frame("asset")),
            {
                "steps": 2,
                "step_1_type": DriveToPose,
                "step_2_type": TakeImage,
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
    assert len(mission.steps) == expected_return["steps"]
    if not len(mission.steps) == 0:
        assert isinstance(mission.steps[0], expected_return["step_1_type"])
        assert isinstance(mission.steps[1], expected_return["step_2_type"])


def test_get_echo_mission_raises_when_empty_mission(echo_service, mocker):
    mock_return = {
        "robotPlanId": 76,
        "planItems": [
            {
                "planItemId": 1227,
                "tag": "wrong_tag",
                "senorTypes": [{"sensorTypeKey": "Picture"}],
                "sortingOrder": 0,
                "robotPlanId": 76,
            },
        ],
    }
    mocker.patch.object(EchoPlanner, "_mission_plan", return_value=mock_return)
    mocker.patch.object(
        StidService,
        "tag_position",
        side_effect=RequestException,
    )
    with pytest.raises(MissionPlannerError):
        echo_service.get_mission(mission_id=76)
