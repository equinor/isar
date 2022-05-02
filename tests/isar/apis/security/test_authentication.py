import json
from http import HTTPStatus

import pytest
from jose import jwt


def mock_access_token():
    token = jwt.encode(claims={}, key="some_key")

    return token


class TestAuthentication:
    @pytest.mark.parametrize(
        "query_string, token, expected_output, expected_status_code",
        [
            (
                "start-mission?ID=1",
                "Dummy Token",
                {"detail": "Invalid token format"},
                HTTPStatus.UNAUTHORIZED,
            ),
            (
                "start-mission?ID=1",
                mock_access_token(),
                {"detail": "Unable to verify token, no signing keys found"},
                HTTPStatus.UNAUTHORIZED,
            ),
            (
                "stop-mission",
                mock_access_token(),
                {"detail": "Unable to verify token, no signing keys found"},
                HTTPStatus.UNAUTHORIZED,
            ),
            (
                "drive-to?x-value=1&y-value=2&z-value=3&quaternion=0&quaternion=0&quaternion=0&quaternion=1",  # noqa: E501
                mock_access_token(),
                {"detail": "Unable to verify token, no signing keys found"},
                HTTPStatus.UNAUTHORIZED,
            ),
        ],
    )
    def test_authentication(
        self,
        client_auth,
        query_string,
        token,
        expected_output,
        expected_status_code,
    ):

        response = client_auth.post(
            f"schedule/{query_string}",
            headers={"Authorization": "Bearer " + token},
        )
        result_message = json.loads(response.text)

        assert result_message == expected_output
        assert response.status_code == expected_status_code
