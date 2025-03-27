import logging
import os
from queue import Empty, Queue

import backoff
from paho.mqtt import client as mqtt
from paho.mqtt.client import Client

from isar.config.settings import settings
from robot_interface.telemetry.mqtt_client import MqttClientInterface


def _on_success(data: dict) -> None:
    logging.getLogger("mqtt_client").info("Connected to MQTT Broker")
    logging.getLogger("mqtt_client").debug(
        f"Elapsed time: {data['elapsed']}, Tries: {data['tries']}"
    )


def _on_backoff(data: dict) -> None:
    logging.getLogger("mqtt_client").warning(
        f"Failed to connect, retrying in {data['wait']} seconds"
    )


def _on_giveup(data: dict) -> None:
    logging.getLogger("mqtt_client").error(
        "Failed to connect to MQTT Broker within set backoff strategy."
    )


class MqttClient(MqttClientInterface):
    def __init__(self, mqtt_queue: Queue) -> None:
        self.logger = logging.getLogger("mqtt_client")
        self.logger.setLevel("INFO")
        self.mqtt_queue: Queue = mqtt_queue

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

        self.client: Client = Client(mqtt.CallbackAPIVersion.VERSION1)

        self.client.enable_logger(logger=self.logger)

        dirname = os.path.dirname(__file__)

        if settings.MQTT_SSL_ENABLED:
            cert_path = os.path.join(dirname, "../../../config/certs/ca-cert.pem")
            self.client.tls_set(ca_certs=cert_path)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        self.client.username_pw_set(username=username, password=password)

    def run(self) -> None:
        self.connect(host=self.host, port=self.port)
        self.client.loop_start()

        while True:
            if not self.client.is_connected():
                continue
            try:
                topic, payload, qos, retain = self.mqtt_queue.get(timeout=1)
            except Empty:
                continue

            self.publish(topic=topic, payload=payload, qos=qos, retain=retain)

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connection returned result: " + mqtt.connack_string(rc))

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT Broker")

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

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        self.logger.debug("Publishing message to topic: %s", topic)
        self.client.publish(topic=topic, payload=payload, qos=qos, retain=retain)
