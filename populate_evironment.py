import os
from argparse import ArgumentParser, Namespace

from isar.config import config
from isar.config.keyvault.keyvault_service import Keyvault

environment: dict = {
    "AZURE_CLIENT_ID": config.get("environment", "azure_client_id"),
    "AZURE_TENANT_ID": config.get("environment", "azure_tenant_id"),
    "EQROBOT_ENVIRONMENT": config.get("environment", "eqrobot_environment"),
    "ENVIRONMENT": os.getenv("ENVIRONMENT"),
    "FLASK_ENV": config.get("environment", "flask_env"),
    "FLASK_RUN_HOST": config.get("environment", "flask_run_host"),
    "FLASK_RUN_PORT": config.get("environment", "flask_run_port"),
    "JWT_DECODE_AUDIENCE": config.get("environment", "jwt_decode_audience"),
    "AZURE_KEYS_URL": config.get("environment", "azure_keys_url"),
}

# These are secrets which will be collected from the Azure Keyvault.
# Each key is the name of the environment variable, while each value is the name of the secret in the keyvault.
secrets: dict = {
    "AZURE_STORAGE_CONNECTION_STRING": "AZURE-STORAGE-CONNECTION-STRING",
    "API_USERNAME": "API-USERNAME",
    "API_PASSWORD": "API-PASSWORD",
}


def populate_environment() -> None:
    parser: ArgumentParser = ArgumentParser(
        description="Populate environment variables in .env"
    )
    parser.add_argument(
        "--client-secret",
        dest="AZURE_CLIENT_SECRET",
        type=str,
        help="Client secret which gives access to the relevant Azure Keyvault",
    )

    args: Namespace = parser.parse_args()
    environment["AZURE_CLIENT_SECRET"] = args.AZURE_CLIENT_SECRET

    keyvault: Keyvault = Keyvault(
        keyvault_name=config.get("azure", "keyvault"),
        client_id=environment["AZURE_CLIENT_ID"],
        client_secret=environment["AZURE_CLIENT_SECRET"],
        tenant_id=environment["AZURE_TENANT_ID"],
    )

    for env_variable, secret_name in secrets.items():
        environment[env_variable] = keyvault.get_secret(secret_name=secret_name).value

    env_file = open(".env", "w")
    for env_variable, value in environment.items():
        env_file.write(f"{env_variable}={value}\n")


if __name__ == "__main__":
    populate_environment()
