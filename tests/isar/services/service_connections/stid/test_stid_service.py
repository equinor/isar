import pytest
from alitra import Frame, Position
from azure.identity._credentials.default import DefaultAzureCredential

from isar.services.service_connections.request_handler import RequestHandler
from tests.mocks.request import MockRequests
from tests.mocks.token import MockToken


@pytest.mark.parametrize(
    "tag, expected_position, mock_return",
    [
        (
            "334-LD-0225",
            Position(x=20196.2000, y=5248.4740, z=15.2080, frame=Frame("asset")),
            MockRequests(
                json_data={
                    "xCoordinate": 20196200.0,
                    "yCoordinate": 5248474.0,
                    "zCoordinate": 15208.0,
                }
            ),
        ),
    ],
)
def test_get_position(stid_service, mocker, tag, expected_position, mock_return):
    mocker.patch.object(DefaultAzureCredential, "get_token", return_value=MockToken())
    mocker.patch.object(RequestHandler, "get", return_value=mock_return)
    position: Position = stid_service.tag_position(tag=tag)
    assert position == expected_position
