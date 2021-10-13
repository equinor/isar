import logging
import traceback

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import KeyVaultSecret, SecretClient

from isar.config.keyvault.keyvault_error import KeyvaultError


class Keyvault:
    def __init__(
        self,
        keyvault_name: str,
        client_id: str = None,
        client_secret: str = None,
        tenant_id: str = None,
    ):
        self.url = "https://" + keyvault_name + ".vault.azure.net"
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.logger = logging.getLogger("API")

    def get_secret(self, secret_name: str) -> KeyVaultSecret:
        secret_client: SecretClient = self.get_secret_client()
        try:
            secret: KeyVaultSecret = secret_client.get_secret(name=secret_name)
        except ResourceNotFoundError:
            self.logger.error("Secret was not found in keyvault.")
            traceback.print_exc()
            raise KeyvaultError  # type: ignore
        except HttpResponseError:
            self.logger.error(
                "An error occurred while retrieving a secret from keyvault."
            )
            traceback.print_exc()
            raise KeyvaultError  # type: ignore

        return secret

    def set_secret(self, secret_name: str, secret_value) -> None:
        secret_client: SecretClient = self.get_secret_client()
        try:
            secret_client.set_secret(name=secret_name, value=secret_value)
        except HttpResponseError:
            self.logger.error("An error occurred while setting a secret in keyvault.")
            traceback.print_exc()
            raise KeyvaultError  # type: ignore

    def get_secret_client(self):
        try:
            if self.client_id and self.client_secret and self.tenant_id:
                credential: ClientSecretCredential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
            else:
                credential: DefaultAzureCredential = DefaultAzureCredential()
        except ClientAuthenticationError:
            self.logger.error("Failed to authenticate to Azure.")
            traceback.print_exc()
            raise KeyvaultError

        secret_client = SecretClient(vault_url=self.url, credential=credential)
        return secret_client
