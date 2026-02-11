from azure.core.credentials import AccessToken
from azure.identity import DefaultAzureCredential

from isar.config.settings import settings


def get_access_token() -> AccessToken:
    credential = DefaultAzureCredential()
    accesstoken = credential.get_token(
        "https://ossrdbms-aad.database.windows.net/.default"
    )
    return accesstoken


def get_db_connection_string() -> str:
    token_env = get_access_token().token
    password_env = token_env

    ssl_mode = "?sslmode=require"

    return (
        f"postgresql://"
        f"{settings.DATABASE_USER}:{password_env}@"
        f"{settings.DATABASE_SERVER_NAME}:5432/isar{ssl_mode}"
    )
