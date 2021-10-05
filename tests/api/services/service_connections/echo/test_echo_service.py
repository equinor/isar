from typing import Optional, Union
import pytest

from isar.models.mission import Mission
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from models.geometry.frame import Frame
from models.geometry.position import Position
from models.planning.step import DriveToPose, TakeImage, TakeThermalImage
from tests.utilities import MockRequests


@pytest.mark.parametrize(
    "id, mock_return, mock_stid, expected_return",
    [
        (
            76,
            MockRequests(
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
                }
            ),
            Position(x=1, y=1, z=0, frame=Frame.Asset),
            {
                "mission_steps": 3,
                "mission_step_1_type": DriveToPose,
                "mission_step_2_type": TakeThermalImage,
            },
        ),
        (
            76,
            MockRequests(
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
                }
            ),
            Position(x=1, y=1, z=0, frame=Frame.Asset),
            {
                "mission_steps": 2,
                "mission_step_1_type": DriveToPose,
                "mission_step_2_type": TakeImage,
            },
        ),
        (
            105,
            MockRequests(
                {
                    "robotPlanId": 76,
                    "planItems": [
                        {
                            "planItemId": 1227,
                            "tag": "334-LD-0225",
                            "sortingOrder": 0,
                            "robotPlanId": 76,
                        },
                    ],
                }
            ),
            None,
            {
                "mission_steps": 0,
                "mission_step_1_type": None,
                "mission_step_2_type": None,
            },
        ),
        (
            125,
            MockRequests(
                {
                    "robotPlanId": 76,
                    "planItems": [
                        {
                            "planItemId": 1227,
                            "tag": "334-LD-0",
                            "sortingOrder": 0,
                            "robotPlanId": 76,
                        },
                    ],
                }
            ),
            None,
            {
                "mission_steps": 0,
                "mission_step_1_type": None,
                "mission_step_2_type": None,
            },
        ),
    ],
)
def test_get_echo_mission(
    echo_service, mocker, id, mock_return, mock_stid, expected_return
):
    mocker.patch.object(RequestHandler, "get", return_value=mock_return)
    mocker.patch.object(StidService, "tag_position", return_value=mock_stid)
    mission: Optional[Mission] = echo_service.get_mission(id)
    assert len(mission.mission_steps) == expected_return["mission_steps"]
    if not len(mission.mission_steps) == 0:
        assert isinstance(
            mission.mission_steps[0], expected_return["mission_step_1_type"]
        )
        assert isinstance(
            mission.mission_steps[1], expected_return["mission_step_2_type"]
        )
