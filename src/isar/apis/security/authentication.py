from typing import Union

from fastapi.security.base import SecurityBase
from injector import inject
from pydantic import BaseModel, AnyHttpUrl
from isar.config import config
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer


class Token(BaseModel):
    access_token: str
    token_type: str


class NoSecurity(SecurityBase):
    def __init__(self) -> None:
        self.scheme_name = "No Security"


class Authenticator:
    def __init__(
        self,
        host: str = config.get("fastapi", "run_host"),
        port: int = config.getint("fastapi", "run_port"),
        openapi_client_id: str = config.get("fastapi", "openapi_client_id"),
        authentication_enabled: bool = config.getboolean(
            "fastapi", "authentication_enabled"
        ),
    ) -> None:
        self.backend_cors_origins: list[Union[str, AnyHttpUrl]] = [
            f"http://{host}:{port}"
        ]
        self.openapi_client_id: str = openapi_client_id
        self.authentication_enabled: bool = authentication_enabled

    @staticmethod
    def get_azure_scheme():
        app_client_id = config.get("fastapi", "app_client_id")
        return SingleTenantAzureAuthorizationCodeBearer(
            app_client_id=app_client_id,
            tenant_id=config.get("environment", "azure_tenant_id"),
            scopes={
                f"api://{app_client_id}/user_impersonation": "user_impersonation",
            },
        )

    @classmethod
    def get_scheme(cls):
        authentication_enabled = config.getboolean("fastapi", "authentication_enabled")
        if authentication_enabled:
            return cls.get_azure_scheme()
        return NoSecurity

    async def load_config(self):
        """
        Load OpenID config on startup.
        """
        if self.authentication_enabled:
            await self.get_azure_scheme().openid_config.load_config()
        else:
            pass
