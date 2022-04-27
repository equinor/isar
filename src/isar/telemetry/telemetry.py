import logging

import backoff
from paho.mqtt import client as mqtt
from paho.mqtt.client import Client

from isar.config.settings import settings
from robot_interface.models.telemetry.entity import Entity


class Telemetry:
    """This is a wrapper for the mqtt client."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("mqtt_client")

        self.client: Client = Client()
        self.client.enable_logger(logger=self.logger)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        username: str = settings.MQTT_USERNAME
        password: str = settings.MQTT_PASSWORD

        self.client.username_pw_set(username=username, password=password)

        self._connect(host=settings.MQTT_HOST, port=settings.MQTT_PORT)
        self.client.loop_start()

    def publish(self, topic: str, payload: Entity, qos=0, retain=False):
        """Publish payload to MQTT topic

        Parameters
        ----------
        topic : string
            MQTT topic
        payload : Entity
            Payload entity generated for MQTT
        qos : integer
            Quality of Service
        retain : boolean
            Retain on topic

        Returns
        -------

        """
        self.client.publish(topic, payload, qos, retain)

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connection returned result: " + mqtt.connack_string(rc))

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT Broker")

    @staticmethod
    def _on_success(data: dict) -> None:
        logging.getLogger("mqtt_client").info("Connected to MQTT Broker")
        logging.getLogger("mqtt_client").debug(
            f"Elapsed time: {data['elapsed']}, Tries: {data['tries']}"
        )

    @staticmethod
    def _on_backoff(data: dict) -> None:
        logging.getLogger("mqtt_client").warning(
            f"Failed to connect, retrying in {data['wait']} seconds"
        )

    @staticmethod
    def _on_giveup(data: dict) -> None:
        logging.getLogger("mqtt_client").error(
            "Failed to connect to MQTT Broker within set backoff strategy."
        )

    @backoff.on_exception(
        backoff.expo,
        ConnectionRefusedError,
        max_time=300,
        on_success=_on_success,
        on_backoff=_on_backoff,
        on_giveup=_on_giveup,
    )
    def _connect(self, host: str, port: int) -> None:
        self.logger.info("Attempting to connect to MQTT Broker")
        self.logger.debug(f"Host: {host}, Port: {port}")
        self.client.connect(host=host, port=port)
