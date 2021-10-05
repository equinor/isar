import pytest
from isar.services.service_connections.request_handler import RequestHandler
from models.geometry.frame import Frame
from models.geometry.position import Position

from tests.utilities import MockRequests


@pytest.mark.parametrize(
    "tag, expected_position, mock_return",
    [
        (
            "334-LD-0225",
            Position(x=20196.2000, y=5248.4740, z=15.2080, frame=Frame.Asset),
            MockRequests(
                json_data={
                    "xCoordinate": 20196200.0,
                    "yCoordinate": 5248474.0,
                    "zCoordinate": 15208.0,
                }
            ),
        ),
        (
            "DO-313-1021",
            None,
            MockRequests(
                json_data={
                    "xCoordinate": None,
                    "yCoordinate": None,
                    "zCoordinate": None,
                }
            ),
        ),
    ],
)
def test_get_position(stid_service, mocker, tag, expected_position, mock_return):
    mocker.patch.object(RequestHandler, "get", return_value=mock_return)
    position: Position = stid_service.tag_position(tag=tag)
    assert position == expected_position
