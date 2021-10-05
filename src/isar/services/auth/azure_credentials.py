import logging

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential


class AzureCredentials:
    @staticmethod
    def get_azure_credentials():
        try:
            return DefaultAzureCredential()
        except ClientAuthenticationError as e:
            logging.error(e.message)
            raise e
