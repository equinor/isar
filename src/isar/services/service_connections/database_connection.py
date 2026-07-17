import logging
import os
from functools import lru_cache

from azure.core.credentials import AccessToken, TokenCredential
from azure.identity import (
    ChainedTokenCredential,
    ClientSecretCredential,
    WorkloadIdentityCredential,
)

from isar.config.settings import settings

logger = logging.getLogger("api")

# Default path where the azure-workload-identity mutating webhook projects the
# service-account token in the pod. Present in cloud (AKS) deployments that
# annotate the pod with `azure.workload.identity/use: "true"`; absent locally
# and in GitHub Actions runners.
_DEFAULT_FEDERATED_TOKEN_FILE = "/var/run/secrets/azure/tokens/azure-identity-token"

# Scope for Entra-ID access tokens accepted by Azure Database for PostgreSQL
# flexible server (used as the Postgres password).
_AZURE_POSTGRES_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


@lru_cache(maxsize=1)
def _get_credential() -> TokenCredential:
    """Build a TokenCredential for Entra-ID auth against Postgres.

    The set of credential types to try is configured via
    ``settings.allowed_auth_methods``, an ordered list whose entries may be
    ``"WorkloadIdentity"`` and/or ``"ClientSecret"`` (case-insensitive). When
    more than one method is configured, the order determines the order inside
    the resulting ``ChainedTokenCredential``.

    In cloud (AKS with Azure Workload Identity), the standard
    ``AZURE_FEDERATED_TOKEN_FILE`` environment variable is injected by the
    azure-workload-identity mutating webhook, and ``WorkloadIdentityCredential``
    exchanges the projected service-account token for an Entra-ID access
    token. For local development, include ``"ClientSecret"`` in
    ``ISAR_ALLOWED_AUTH_METHODS`` and provide ``ISAR_AZURE_CLIENT_SECRET``.

    Cached so a single credential instance is shared by all callers and the
    underlying token is reused across calls.
    """
    token_file_path = os.environ.get(
        "AZURE_FEDERATED_TOKEN_FILE", _DEFAULT_FEDERATED_TOKEN_FILE
    )
    client_secret = os.environ.get("ISAR_AZURE_CLIENT_SECRET")

    credentials: list[TokenCredential] = []
    activated: list[str] = []

    for method in settings.allowed_auth_methods:
        normalized = method.strip().lower()
        if normalized == "workloadidentity":
            if os.path.exists(token_file_path):
                credentials.append(
                    WorkloadIdentityCredential(
                        tenant_id=settings.AZURE_TENANT_ID,
                        client_id=settings.AZURE_CLIENT_ID,
                        token_file_path=token_file_path,
                    )
                )
                activated.append("WorkloadIdentityCredential")
            else:
                logger.warning(
                    "ISAR_ALLOWED_AUTH_METHODS includes 'WorkloadIdentity' but "
                    f"no federated token file found at '{token_file_path}'; "
                    "skipping WorkloadIdentityCredential."
                )
        elif normalized == "clientsecret":
            if client_secret and not client_secret.lower().startswith("fill in"):
                credentials.append(
                    ClientSecretCredential(
                        tenant_id=settings.AZURE_TENANT_ID,
                        client_id=settings.AZURE_CLIENT_ID,
                        client_secret=client_secret,
                    )
                )
                activated.append("ClientSecretCredential")
            else:
                logger.warning(
                    "ISAR_ALLOWED_AUTH_METHODS includes 'ClientSecret' but "
                    "ISAR_AZURE_CLIENT_SECRET is missing/placeholder; skipping "
                    "ClientSecretCredential."
                )
        else:
            logger.warning(
                f"Unknown auth method '{method}' in ISAR_ALLOWED_AUTH_METHODS; "
                "expected 'WorkloadIdentity' or 'ClientSecret'."
            )

    if not credentials:
        raise RuntimeError(
            "No usable Azure credential could be constructed from "
            "ISAR_ALLOWED_AUTH_METHODS. Configure at least one of "
            "'WorkloadIdentity' (with a federated token file present at "
            f"'{token_file_path}') or 'ClientSecret' (with "
            "ISAR_AZURE_CLIENT_SECRET set)."
        )

    if len(credentials) == 1:
        logger.info(f"Database auth using {activated[0]} only")
        return credentials[0]

    logger.info("Database auth using ChainedTokenCredential: " + " -> ".join(activated))
    return ChainedTokenCredential(*credentials)


def get_access_token() -> AccessToken:
    credential = _get_credential()
    return credential.get_token(_AZURE_POSTGRES_SCOPE)


def get_db_connection_string() -> str:
    token = get_access_token().token

    ssl_mode = "?sslmode=require"

    return (
        f"postgresql://"
        f"{settings.DATABASE_USER}:{token}@"
        f"{settings.DATABASE_SERVER_NAME}:5432/isar{ssl_mode}"
    )
