import atexit
import logging
import os
import time
from tempfile import NamedTemporaryFile
from typing import Any

import backoff
from backoff.types import Details
from paho.mqtt import client as mqtt
from paho.mqtt.client import Client
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue, MQTTQueueMessage


def _on_success(data: Details) -> None:
    logging.getLogger("mqtt_client").info("Connected to MQTT Broker")
    logging.getLogger("mqtt_client").debug(
        f"Elapsed time: {data['elapsed']}, Tries: {data['tries']}"
    )


def _on_backoff(data: Details) -> None:
    if "wait" in data:
        logging.getLogger("mqtt_client").warning(
            f"Failed to connect, retrying in {data['wait']} seconds"
        )


def _on_giveup(data: Details) -> None:
    logging.getLogger("mqtt_client").error(
        "Failed to connect to MQTT Broker within set backoff strategy."
    )


def _remove_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


# paho wants a path, not the certificate itself, so an inline certificate has to
# be spilled to disk. Cached by content so that constructing several clients does
# not leave a file behind for each of them, and removed when ISAR exits.
# The deployments run with a read-only root filesystem and an emptyDir at /tmp,
# which is where this lands.
_inline_certificate_paths: dict[str, str] = {}


def _write_inline_certificate(certificate: str) -> str:
    if certificate in _inline_certificate_paths:
        return _inline_certificate_paths[certificate]

    with NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as certificate_file:
        certificate_file.write(certificate)

    _inline_certificate_paths[certificate] = certificate_file.name
    atexit.register(_remove_file, certificate_file.name)

    return certificate_file.name


class MqttClient:
    def __init__(self, mqtt_queue: MQTTQueue) -> None:
        self.logger = logging.getLogger("mqtt_client")
        self.logger.setLevel("INFO")
        self.mqtt_queue: MQTTQueue = mqtt_queue

        username: str = settings.MQTT_USERNAME
        password: str = ""
        try:
            password = os.environ["ISAR_MQTT_PASSWORD"]
        except KeyError:
            self.logger.warning(
                "Failed to retrieve ISAR_MQTT_PASSWORD from environment. Attempting "
                "with empty string as password."
            )

        self.host: str = settings.MQTT_HOST

        # Fix for mqtt running on localhost in docker
        if "IS_DOCKER" in os.environ and self.host == "localhost":
            self.host = "host.docker.internal"

        self.port: int = settings.MQTT_PORT

        self.client: Client = Client(
            protocol=mqtt.MQTTv5, callback_api_version=CallbackAPIVersion.VERSION2
        )

        self.client.enable_logger(logger=self.logger)

        dirname = os.path.dirname(__file__)

        if settings.MQTT_SSL_ENABLED:
            self.client.tls_set(ca_certs=self._resolve_ca_certificate(dirname))

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        self.client.username_pw_set(username=username, password=password)

    def _resolve_ca_certificate(self, dirname: str) -> str:
        """Determine which CA certificate to verify the broker certificate against.

        Parameters
        ----------
        dirname : str
            Directory of this module, used to locate the bundled certificate.

        Returns
        -------
        str
            Path to the CA certificate to use.
        """
        if settings.MQTT_CA_CERT:
            return _write_inline_certificate(settings.MQTT_CA_CERT)

        if settings.MQTT_CA_CERT_PATH:
            return settings.MQTT_CA_CERT_PATH

        return os.path.join(dirname, "../../../config/certs/ca-cert.pem")

    def run(self) -> None:
        self.connect(host=self.host, port=self.port)
        self.client.loop_start()

        while True:
            time.sleep(0)  # avoid CPU spin
            if not self.client.is_connected():
                continue
            item: MQTTQueueMessage = self.mqtt_queue.get(timeout=1)
            if item is None:
                continue

            self.logger.debug("Publishing message to topic: %s", item.topic)
            self.client.publish(
                topic=item.topic,
                payload=item.payload,
                qos=item.qos,
                retain=item.retain,
                properties=item.properties,
            )

    def on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: dict[str, Any],
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        self.logger.info(f"Connected: {reason_code}")

    def on_disconnect(
        self,
        client: Client,
        ignored: Any,
        disconnectFlags: mqtt.DisconnectFlags,
        reasonCode: ReasonCode,
        properties: Properties | None,
    ) -> None:
        self.logger.warning(f"Unexpected disconnect: {reasonCode}.")

    @backoff.on_exception(
        backoff.expo,
        ConnectionRefusedError,
        max_time=300,
        on_success=_on_success,
        on_backoff=_on_backoff,
        on_giveup=_on_giveup,
    )
    def connect(self, host: str, port: int) -> None:
        self.logger.info("Attempting to connect to MQTT Broker")
        self.logger.info("Host: %s, Port: %s", host, port)
        self.client.connect(host=host, port=port)
