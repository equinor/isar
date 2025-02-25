from http import HTTPStatus

import jwt
import pytest
from fastapi.testclient import TestClient


def mock_access_token():
    token = jwt.encode(payload={}, key="some_key")

    return token


class TestAuthentication:
    @pytest.mark.parametrize(
        "query_string",
        ["start-mission?ID=1", "stop-mission"],
    )
    def test_authentication(
        self,
        client_auth: TestClient,
        query_string: str,
    ):
        token = mock_access_token()
        expected_status_code = HTTPStatus.UNAUTHORIZED

        response = client_auth.post(
            f"schedule/{query_string}",
            headers={"Authorization": "Bearer " + token},
        )

        assert response.status_code == expected_status_code
