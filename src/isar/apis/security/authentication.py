import logging

from fastapi.security.base import SecurityBase
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from pydantic import BaseModel

from isar.config import config


class Token(BaseModel):
    access_token: str
    token_type: str


class NoSecurity(SecurityBase):
    def __init__(self) -> None:
        self.scheme_name = "No Security"


class Authenticator:
    def __init__(
        self,
        app_client_id: str = config.get("authentication", "app_client_id"),
        tenant_id: str = config.get("authentication", "azure_tenant_id"),
        openapi_client_id: str = config.get("authentication", "openapi_client_id"),
        authentication_enabled: bool = config.getboolean(
            "authentication", "authentication_enabled"
        ),
    ) -> None:
        self.logger = logging.getLogger("api")
        self.app_client_id: str = app_client_id
        self.tenant_id: str = tenant_id
        self.openapi_client_id: str = openapi_client_id

        self.authentication_enabled: bool = authentication_enabled

        enabled_string = "enabled" if self.authentication_enabled else "disabled"
        self.logger.info(f"API authentication is {enabled_string}")

    def should_authenticate(self):
        return self.authentication_enabled

    def get_azure_scheme(self):
        return SingleTenantAzureAuthorizationCodeBearer(
            app_client_id=self.app_client_id,
            tenant_id=self.tenant_id,
            scopes={
                f"api://{self.app_client_id}/user_impersonation": "user_impersonation",
            },
        )

    def get_scheme(self):
        if self.should_authenticate():
            return self.get_azure_scheme()
        return NoSecurity

    async def load_config(self):
        """
        Load OpenID config on startup.
        """
        if self.should_authenticate():
            await self.get_azure_scheme().openid_config.load_config()
        else:
            pass
