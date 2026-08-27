from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from isar.models.mqtt_queue import MQTTQueue
from isar.services.service_connections.mqtt import mqtt_client
from isar.services.service_connections.mqtt.mqtt_client import MqttClient

CERTIFICATE = (
    "-----BEGIN CERTIFICATE-----\nnot-a-real-certificate\n-----END CERTIFICATE-----\n"
)


@pytest.fixture
def client(mocker: MockerFixture) -> MqttClient:
    mocker.patch.object(mqtt_client.settings, "MQTT_SSL_ENABLED", False)
    return MqttClient(mqtt_queue=MQTTQueue())


class TestResolveCaCertificate:
    def test_bundled_certificate_is_used_by_default(
        self, client: MqttClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(mqtt_client.settings, "MQTT_CA_CERT", "")
        mocker.patch.object(mqtt_client.settings, "MQTT_CA_CERT_PATH", "")

        dirname = str(Path(mqtt_client.__file__).parent)
        resolved = Path(client._resolve_ca_certificate(dirname)).resolve()

        assert resolved.name == "ca-cert.pem"
        assert resolved.is_file()

    def test_configured_path_is_used_when_set(
        self, client: MqttClient, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        certificate_path = tmp_path / "ca.pem"
        certificate_path.write_text(CERTIFICATE)
        mocker.patch.object(mqtt_client.settings, "MQTT_CA_CERT", "")
        mocker.patch.object(
            mqtt_client.settings, "MQTT_CA_CERT_PATH", str(certificate_path)
        )

        assert client._resolve_ca_certificate("") == str(certificate_path)

    def test_inline_certificate_takes_precedence_over_path(
        self, client: MqttClient, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch.object(mqtt_client.settings, "MQTT_CA_CERT", CERTIFICATE)
        mocker.patch.object(
            mqtt_client.settings, "MQTT_CA_CERT_PATH", str(tmp_path / "ca.pem")
        )

        resolved = Path(client._resolve_ca_certificate(""))

        assert resolved.read_text() == CERTIFICATE

    def test_inline_certificate_is_written_once_and_cleaned_up(
        self, client: MqttClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(mqtt_client.settings, "MQTT_CA_CERT", CERTIFICATE)
        mocker.patch.object(mqtt_client.settings, "MQTT_CA_CERT_PATH", "")

        first = client._resolve_ca_certificate("")
        second = client._resolve_ca_certificate("")

        assert first == second, "each client must not leave its own certificate behind"

        mqtt_client._remove_file(first)
        assert not Path(first).exists()
