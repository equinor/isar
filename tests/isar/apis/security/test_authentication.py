from http import HTTPStatus

import jwt
import pytest
from fastapi.testclient import TestClient
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from fastapi_azure_auth.auth import AzureAuthorizationCodeBearerBase
from fastapi_azure_auth.user import User
from pydantic import ValidationError
from pytest import MonkeyPatch

from isar.apis.security.authentication import build_azure_scheme
from isar.config.settings import settings


def advertised_scopes(scheme: AzureAuthorizationCodeBearerBase) -> dict[str, str]:
    """Scopes offered by Swagger's Authorize button, for the given scheme."""
    return scheme.oauth.model.flows.authorizationCode.scopes


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
        assert scheme.openid_config.config_url is None
        assert scheme.openid_config.tenant_id == settings.AZURE_TENANT_ID
        assert scheme.app_client_id == settings.AZURE_CLIENT_ID

    def test_openid_config_url_is_honoured(self, monkeypatch: MonkeyPatch) -> None:
        config_url = (
            "http://keycloak:8080/realms/robotics/.well-known/openid-configuration"
        )
        authorization_url = (
            "http://keycloak:8080/realms/robotics/protocol/openid-connect/auth"
        )
        token_url = "http://keycloak:8080/realms/robotics/protocol/openid-connect/token"

        monkeypatch.setattr(settings, "OPENID_CONFIG_URL", config_url)
        monkeypatch.setattr(settings, "OPENAPI_AUTHORIZATION_URL", authorization_url)
        monkeypatch.setattr(settings, "OPENAPI_TOKEN_URL", token_url)

        scheme = build_azure_scheme()

        assert not isinstance(scheme, SingleTenantAzureAuthorizationCodeBearer)
        assert isinstance(scheme, AzureAuthorizationCodeBearerBase)
        assert scheme.openid_config.config_url == config_url
        assert scheme.authorization_url == authorization_url
        assert scheme.token_url == token_url
        assert scheme.app_client_id == settings.AZURE_CLIENT_ID
        assert scheme.validate_iss is True

    def test_openapi_urls_fall_back_to_azure_when_unset(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            settings,
            "OPENID_CONFIG_URL",
            "http://keycloak:8080/realms/robotics/.well-known/openid-configuration",
        )
        monkeypatch.setattr(settings, "OPENAPI_AUTHORIZATION_URL", None)
        monkeypatch.setattr(settings, "OPENAPI_TOKEN_URL", None)

        scheme = build_azure_scheme()

        assert scheme.authorization_url is not None
        assert settings.AZURE_TENANT_ID in scheme.authorization_url

    def test_scope_defaults_to_the_entra_shaped_scope(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "OPENID_SCOPE", None)

        scheme = build_azure_scheme()

        expected = f"api://{settings.AZURE_CLIENT_ID}/user_impersonation"
        assert advertised_scopes(scheme) == {expected: "user_impersonation"}

    def test_openid_scope_is_honoured(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "OPENID_SCOPE", "isar-api")

        scheme = build_azure_scheme()

        assert advertised_scopes(scheme) == {"isar-api": "isar-api"}
        assert scheme.app_client_id == settings.AZURE_CLIENT_ID


class TestAudienceClaimShape:
    """Pin the audience shapes ISAR accepts.

    ``fastapi_azure_auth`` declares ``aud`` as a plain ``str``, so the array form
    RFC 7519 also permits is rejected with an opaque 401. Asserted here so that a
    dependency upgrade lifting the restriction is noticed.
    """

    def test_string_audience_is_accepted(self) -> None:
        user = User(
            aud=settings.AZURE_CLIENT_ID,
            claims={},
            access_token="",
            iss="",
            sub="",
            exp=0,
            iat=0,
            nbf=0,
            ver="2.0",
        )

        assert user.aud == settings.AZURE_CLIENT_ID

    def test_array_audience_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            User(
                aud=[settings.AZURE_CLIENT_ID, "another-audience"],
                claims={},
                access_token="",
                iss="",
                sub="",
                exp=0,
                iat=0,
                nbf=0,
                ver="2.0",
            )
