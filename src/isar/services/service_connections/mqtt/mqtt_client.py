import logging
import os
from abc import ABCMeta, abstractmethod
from typing import Any

from paho.mqtt import client as mqtt
from paho.mqtt.client import Client

from isar.config import config


class MqttClientInterface(metaclass=ABCMeta):
    @abstractmethod
    def publish(
        self, topic: str, payload: Any, qos: int = 0, retain: bool = False
    ) -> None:
        """
        Parameters
        ----------
        topic : string
            MQTT topic to publish to
        payload : Any
            Payload to send to publish on the topic
        qos : integer
            Quality of Service
        retain : boolean
            Retain on topic

        Returns
        -------

        """
        pass


class MqttClient(MqttClientInterface):
    def __init__(self):
        self.logger = logging.getLogger("mqtt_client")

        username: str = config.get("service_connections", "mqtt_username")
        password: str = ""
        try:
            password = os.environ["MQTT_PASSWORD"]
        except KeyError:
            self.logger.warning(
                "Failed to retrieve MQTT_PASSWORD from environment. Attempting with empty string as password."
            )

        host: str = config.get("service_connections", "mqtt_host")
        port: int = config.getint("service_connections", "mqtt_port")

        self.client: Client = Client()

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        self.client.username_pw_set(username=username, password=password)
        self.client.connect(host=host, port=port, keepalive=60)

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connection returned result: " + mqtt.connack_string(rc))

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT Broker")

    def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False):
        self.client.publish(topic=topic, payload=payload, qos=qos, retain=retain)
