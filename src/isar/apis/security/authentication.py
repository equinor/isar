import logging
from typing import Any, Callable, Coroutine, Type

from fastapi import Depends
from fastapi.security.base import SecurityBase
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from fastapi_azure_auth.auth import AzureAuthorizationCodeBearerBase
from fastapi_azure_auth.exceptions import InvalidAuthHttp
from fastapi_azure_auth.user import User
from pydantic import BaseModel

from isar.config.settings import settings


class Token(BaseModel):
    access_token: str
    token_type: str


class NoSecurity(SecurityBase):
    def __init__(self) -> None:
        self.scheme_name = "No Security"


def build_azure_scheme() -> AzureAuthorizationCodeBearerBase:
    """
    Build the security scheme used to validate access tokens.

    By default this is a single tenant Azure Entra ID scheme. If
    ``settings.OPENID_CONFIG_URL`` is set, the OpenID Connect discovery document is
    read from that URL instead, which allows ISAR to be pointed at a different
    OpenID provider such as a local mock issuer used by the integration tests.

    ``SingleTenantAzureAuthorizationCodeBearer`` does not accept an
    ``openid_config_url`` argument, so the base class is used directly in that case.
    Issuer validation remains enabled either way; the expected issuer is taken from
    the discovery document.

    Returns
    -------
    AzureAuthorizationCodeBearerBase
        The configured security scheme.
    """
    scopes: dict[str, str] = {
        f"api://{settings.AZURE_CLIENT_ID}/user_impersonation": "user_impersonation",
    }

    if settings.OPENID_CONFIG_URL:
        return AzureAuthorizationCodeBearerBase(
            app_client_id=settings.AZURE_CLIENT_ID,
            tenant_id=settings.AZURE_TENANT_ID,
            scopes=scopes,
            openid_config_url=settings.OPENID_CONFIG_URL,
            openapi_authorization_url=settings.OPENAPI_AUTHORIZATION_URL,
            openapi_token_url=settings.OPENAPI_TOKEN_URL,
        )

    return SingleTenantAzureAuthorizationCodeBearer(
        app_client_id=settings.AZURE_CLIENT_ID,
        tenant_id=settings.AZURE_TENANT_ID,
        scopes=scopes,
    )


azure_scheme: AzureAuthorizationCodeBearerBase = build_azure_scheme()


async def validate_has_role(user: User = Depends(azure_scheme)) -> None:
    """
    Validate if the user has the required role in order to access the API.
    Raises a 403 authorization error if not.
    """
    if settings.REQUIRED_ROLE not in user.roles:
        raise InvalidAuthHttp(
            "Current user does not possess the required role for this endpoint"
        )


class Authenticator:
    def __init__(
        self,
        authentication_enabled: bool = settings.AUTHENTICATION_ENABLED,
    ) -> None:
        self.logger = logging.getLogger("api")
        self.authentication_enabled: bool = authentication_enabled
        enabled_string = "enabled" if self.authentication_enabled else "disabled"
        self.logger.info("API authentication is %s", enabled_string)

    def should_authenticate(self) -> bool:
        return self.authentication_enabled

    def get_scheme(
        self,
    ) -> Callable[[Any], Coroutine[Any, Any, None]] | Type[NoSecurity]:
        if self.should_authenticate():
            return validate_has_role
        return NoSecurity

    async def load_config(self) -> None:
        """
        Load OpenID config on startup.
        """
        if self.should_authenticate():
            await azure_scheme.openid_config.load_config()
        else:
            pass
