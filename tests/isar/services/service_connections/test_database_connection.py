from pathlib import Path

import pytest
from azure.identity import (
    ChainedTokenCredential,
    ClientSecretCredential,
    WorkloadIdentityCredential,
)
from pytest_mock import MockerFixture

from isar.services.service_connections import database_connection


@pytest.fixture(autouse=True)
def _clear_credential_cache() -> None:
    """The credential is cached with ``lru_cache``; reset between tests."""
    database_connection._get_credential.cache_clear()


def _set_methods(mocker: MockerFixture, methods: list[str]) -> None:
    """Drive ``settings.allowed_auth_methods`` via the underlying string field."""
    mocker.patch.object(
        database_connection.settings, "ALLOWED_AUTH_METHODS", ",".join(methods)
    )


class TestGetCredential:
    def test_workload_identity_only(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        token_file = tmp_path / "azure-identity-token"
        token_file.write_text("dummy-token")
        monkeypatch.setenv("AZURE_FEDERATED_TOKEN_FILE", str(token_file))
        monkeypatch.delenv("ISAR_AZURE_CLIENT_SECRET", raising=False)
        _set_methods(mocker, ["WorkloadIdentity"])

        credential = database_connection._get_credential()

        assert isinstance(credential, WorkloadIdentityCredential)

    def test_client_secret_only(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        monkeypatch.setenv(
            "AZURE_FEDERATED_TOKEN_FILE", str(tmp_path / "does-not-exist")
        )
        monkeypatch.setenv("ISAR_AZURE_CLIENT_SECRET", "some-secret")
        _set_methods(mocker, ["ClientSecret"])

        credential = database_connection._get_credential()

        assert isinstance(credential, ClientSecretCredential)

    def test_chained_in_configured_order(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        token_file = tmp_path / "azure-identity-token"
        token_file.write_text("dummy-token")
        monkeypatch.setenv("AZURE_FEDERATED_TOKEN_FILE", str(token_file))
        monkeypatch.setenv("ISAR_AZURE_CLIENT_SECRET", "some-secret")
        _set_methods(mocker, ["WorkloadIdentity", "ClientSecret"])

        credential = database_connection._get_credential()

        assert isinstance(credential, ChainedTokenCredential)
        assert isinstance(credential.credentials[0], WorkloadIdentityCredential)
        assert isinstance(credential.credentials[1], ClientSecretCredential)

    def test_workload_identity_skipped_when_no_token_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        monkeypatch.setenv(
            "AZURE_FEDERATED_TOKEN_FILE", str(tmp_path / "does-not-exist")
        )
        monkeypatch.setenv("ISAR_AZURE_CLIENT_SECRET", "some-secret")
        _set_methods(mocker, ["WorkloadIdentity", "ClientSecret"])

        credential = database_connection._get_credential()

        assert isinstance(credential, ClientSecretCredential)

    def test_client_secret_skipped_when_placeholder(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        token_file = tmp_path / "azure-identity-token"
        token_file.write_text("dummy-token")
        monkeypatch.setenv("AZURE_FEDERATED_TOKEN_FILE", str(token_file))
        monkeypatch.setenv("ISAR_AZURE_CLIENT_SECRET", "Fill in your secret here")
        _set_methods(mocker, ["WorkloadIdentity", "ClientSecret"])

        credential = database_connection._get_credential()

        assert isinstance(credential, WorkloadIdentityCredential)

    def test_raises_when_no_method_yields_a_credential(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        monkeypatch.setenv(
            "AZURE_FEDERATED_TOKEN_FILE", str(tmp_path / "does-not-exist")
        )
        monkeypatch.delenv("ISAR_AZURE_CLIENT_SECRET", raising=False)
        _set_methods(mocker, ["WorkloadIdentity", "ClientSecret"])

        with pytest.raises(RuntimeError, match="No usable Azure credential"):
            database_connection._get_credential()

    def test_raises_when_allowed_methods_is_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        monkeypatch.setenv("ISAR_AZURE_CLIENT_SECRET", "some-secret")
        _set_methods(mocker, [])

        with pytest.raises(RuntimeError, match="No usable Azure credential"):
            database_connection._get_credential()

    def test_unknown_method_is_ignored(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        monkeypatch.setenv("ISAR_AZURE_CLIENT_SECRET", "some-secret")
        _set_methods(mocker, ["NotARealMethod", "ClientSecret"])

        credential = database_connection._get_credential()

        assert isinstance(credential, ClientSecretCredential)


class TestGetDbConnectionString:
    def test_includes_user_server_token_and_ssl_mode(
        self,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(database_connection.settings, "DATABASE_USER", "isar-app")
        mocker.patch.object(
            database_connection.settings,
            "DATABASE_SERVER_NAME",
            "robotics-dev-psql-server.postgres.database.azure.com",
        )

        # Replace the token acquisition path so the test does not reach Azure.
        fake_token = mocker.MagicMock(token="ENTRA_TOKEN")
        mocker.patch.object(
            database_connection, "get_access_token", return_value=fake_token
        )

        url = database_connection.get_db_connection_string()

        assert url == (
            "postgresql://isar-app:ENTRA_TOKEN@"
            "robotics-dev-psql-server.postgres.database.azure.com:5432/isar"
            "?sslmode=require"
        )
