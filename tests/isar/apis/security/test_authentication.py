from http import HTTPStatus

import jwt
import pytest
from fastapi.testclient import TestClient
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from fastapi_azure_auth.auth import AzureAuthorizationCodeBearerBase
from pytest import MonkeyPatch

from isar.apis.security.authentication import build_azure_scheme
from isar.config.settings import settings


def stub_access_token() -> str:
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
    ) -> None:
        token = stub_access_token()
        expected_status_code = HTTPStatus.UNAUTHORIZED

        response = client_auth.post(
            f"schedule/{query_string}",
            headers={"Authorization": "Bearer " + token},
        )

        assert response.status_code == expected_status_code


class TestBuildAzureScheme:
    def test_defaults_to_single_tenant_azure_scheme(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "OPENID_CONFIG_URL", None)

        scheme = build_azure_scheme()

        assert isinstance(scheme, SingleTenantAzureAuthorizationCodeBearer)
        # No override, so the discovery document URL is derived from the tenant ID
        # and points at Azure Entra ID.
        assert scheme.openid_config.config_url is None
        assert scheme.openid_config.tenant_id == settings.AZURE_TENANT_ID
        assert scheme.app_client_id == settings.AZURE_CLIENT_ID

    def test_openid_config_url_is_honoured(self, monkeypatch: MonkeyPatch) -> None:
        config_url = "http://oauth-mock:8080/.well-known/openid-configuration"
        authorization_url = "http://oauth-mock:8080/authorize"
        token_url = "http://oauth-mock:8080/token"

        monkeypatch.setattr(settings, "OPENID_CONFIG_URL", config_url)
        monkeypatch.setattr(settings, "OPENAPI_AUTHORIZATION_URL", authorization_url)
        monkeypatch.setattr(settings, "OPENAPI_TOKEN_URL", token_url)

        scheme = build_azure_scheme()

        assert not isinstance(scheme, SingleTenantAzureAuthorizationCodeBearer)
        assert isinstance(scheme, AzureAuthorizationCodeBearerBase)
        assert scheme.openid_config.config_url == config_url
        assert scheme.authorization_url == authorization_url
        assert scheme.token_url == token_url
        # The audience is still ISAR's own client ID, and issuer validation stays on.
        assert scheme.app_client_id == settings.AZURE_CLIENT_ID
        assert scheme.validate_iss is True

    def test_openapi_urls_fall_back_to_azure_when_unset(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            settings,
            "OPENID_CONFIG_URL",
            "http://oauth-mock:8080/.well-known/openid-configuration",
        )
        monkeypatch.setattr(settings, "OPENAPI_AUTHORIZATION_URL", None)
        monkeypatch.setattr(settings, "OPENAPI_TOKEN_URL", None)

        scheme = build_azure_scheme()

        assert scheme.authorization_url is not None
        assert settings.AZURE_TENANT_ID in scheme.authorization_url
