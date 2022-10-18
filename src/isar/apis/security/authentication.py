import logging


from fastapi import Depends
from fastapi_azure_auth.exceptions import InvalidAuth
from fastapi_azure_auth.user import User
from fastapi.security.base import SecurityBase
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from pydantic import BaseModel

from isar.config.settings import settings


class Token(BaseModel):
    access_token: str
    token_type: str


class NoSecurity(SecurityBase):
    def __init__(self) -> None:
        self.scheme_name = "No Security"


azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=settings.APP_CLIENT_ID,
    tenant_id=settings.AZURE_TENANT_ID,
    scopes={
        f"api://{settings.APP_CLIENT_ID}/user_impersonation": "user_impersonation",
    },
)


async def validate_has_role(user: User = Depends(azure_scheme)) -> None:
    """
    Validate that a user has the `role` role in order to access the API.
    Raises a 401 authentication error if not.
    """
    if settings.REQUIRED_ROLE not in user.roles:
        raise InvalidAuth(
            "Current user does not possess the required role for this endpoint"
        )


class Authenticator:
    def __init__(
        self,
        openapi_client_id: str = settings.OPENAPI_CLIENT_ID,
        authentication_enabled: bool = settings.AUTHENTICATION_ENABLED,
    ) -> None:
        self.logger = logging.getLogger("api")
        self.openapi_client_id: str = openapi_client_id
        self.authentication_enabled: bool = authentication_enabled
        enabled_string = "enabled" if self.authentication_enabled else "disabled"
        self.logger.info(f"API authentication is {enabled_string}")

    def should_authenticate(self):
        return self.authentication_enabled

    def get_scheme(self):
        if self.should_authenticate():
            return validate_has_role
        return NoSecurity

    async def load_config(self):
        """
        Load OpenID config on startup.
        """
        if self.should_authenticate():
            await azure_scheme.openid_config.load_config()
        else:
            pass
