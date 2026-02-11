from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential

from isar.config.settings import settings


def get_access_token() -> AccessToken:
    credential = DefaultAzureCredential()
    accesstoken = credential.get_token(
        "https://ossrdbms-aad.database.windows.net/.default"
    )
    return accesstoken


def get_db_url() -> str:
    token_env = get_access_token().token
    password_env = token_env

    return (
        f"postgresql://"
        f"postgresuser:{password_env}@"
        f"{settings.DATABASE_SERVER_NAME}:5432/isar"
    )
