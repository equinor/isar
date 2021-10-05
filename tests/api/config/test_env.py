import os

import pytest


@pytest.mark.skip(
    reason="Environment variables currently not present in pytest in DevOps pipeline as environment variables"
)
class TestEnvironmentVariablesPresent:
    def test_azure_credentials_present(self):
        assert os.getenv("AZURE_TENANT_ID") is not None
        assert os.getenv("AZURE_CLIENT_ID") is not None
        assert os.getenv("AZURE_CLIENT_SECRET") is not None
        assert os.getenv("AZURE_STORAGE_CONNECTION_STRING") is not None

    def test_robot_api_credentials_present(self):
        assert os.getenv("API_USERNAME") is not None
        assert os.getenv("API_PASSWORD") is not None

    def test_authentication_env_variables_present(self):
        assert os.getenv("JWT_DECODE_AUDIENCE") is not None
        assert os.getenv("AZURE_KEYS_URL") is not None

    def test_environment_present(self):
        assert os.getenv("ENVIRONMENT") is not None
