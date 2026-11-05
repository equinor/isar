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
    @pytest.mark.parametrize(
        ("config_url", "expected_type"),
        [
            pytest.param(None, SingleTenantAzureAuthorizationCodeBearer, id="azure"),
            pytest.param(
                "http://keycloak:8080/realms/robotics/.well-known/openid-configuration",
                AzureAuthorizationCodeBearerBase,
                id="custom-openid",
            ),
        ],
    )
    def test_selects_configured_identity_provider(
        self,
        monkeypatch: MonkeyPatch,
        config_url: str | None,
        expected_type: type[AzureAuthorizationCodeBearerBase],
    ) -> None:
        monkeypatch.setattr(settings, "OPENID_CONFIG_URL", config_url)

        scheme = build_azure_scheme()

        assert type(scheme) is expected_type
        assert scheme.openid_config.config_url == config_url
        assert scheme.openid_config.tenant_id == settings.AZURE_TENANT_ID

    @pytest.mark.parametrize(
        "config_url",
        [None, "http://keycloak:8080/realms/robotics/.well-known/openid-configuration"],
        ids=["azure", "custom-openid"],
    )
    def test_provider_keeps_client_and_issuer_validation(
        self, monkeypatch: MonkeyPatch, config_url: str | None
    ) -> None:
        monkeypatch.setattr(settings, "OPENID_CONFIG_URL", config_url)

        scheme = build_azure_scheme()

        assert scheme.app_client_id == settings.AZURE_CLIENT_ID
        assert scheme.validate_iss is True

    @pytest.mark.parametrize("custom_urls", [False, True], ids=["fallback", "custom"])
    def test_openapi_urls(self, monkeypatch: MonkeyPatch, custom_urls: bool) -> None:
        authorization_url = (
            "http://keycloak:8080/realms/robotics/protocol/openid-connect/auth"
        )
        token_url = "http://keycloak:8080/realms/robotics/protocol/openid-connect/token"
        monkeypatch.setattr(
            settings,
            "OPENID_CONFIG_URL",
            "http://keycloak:8080/realms/robotics/.well-known/openid-configuration",
        )
        monkeypatch.setattr(
            settings,
            "OPENAPI_AUTHORIZATION_URL",
            authorization_url if custom_urls else None,
        )
        monkeypatch.setattr(
            settings, "OPENAPI_TOKEN_URL", token_url if custom_urls else None
        )
        azure_base = (
            f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0"
        )

        scheme = build_azure_scheme()

        assert (scheme.authorization_url, scheme.token_url) == (
            (authorization_url, token_url)
            if custom_urls
            else (f"{azure_base}/authorize", f"{azure_base}/token")
        )

    @pytest.mark.parametrize("scope", [None, "isar-api"], ids=["default", "custom"])
    def test_advertises_configured_scope(
        self, monkeypatch: MonkeyPatch, scope: str | None
    ) -> None:
        monkeypatch.setattr(settings, "OPENID_SCOPE", scope)
        expected = (
            {"isar-api": "isar-api"}
            if scope
            else {
                f"api://{settings.AZURE_CLIENT_ID}/user_impersonation": "user_impersonation"
            }
        )

        scheme = build_azure_scheme()

        assert advertised_scopes(scheme) == expected
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
