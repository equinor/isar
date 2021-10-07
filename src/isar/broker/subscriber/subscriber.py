import logging
import logging.config
import os
from logging import Logger
from typing import Any

import yaml
from paho.mqtt.client import Client, MQTTMessage

logging.config.dictConfig(yaml.safe_load(open(f"logging.conf")))


class Subscriber:
    def __init__(self) -> None:
        self.logger: Logger = logging.getLogger("broker")
        self.client: Client = Client()
        self.client.username_pw_set(
            username=os.getenv("VERNEMQ_USER"), password=os.getenv("VERNEMQ_PASSWORD")
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            self.client.connect("mqtt_broker", 1883, 60)
        except ConnectionRefusedError as e:
            self.logger.info(
                "First attempt to connect fails because the docker container for the MQTT server needs to start."
            )

    def on_connect(self, client: Client, userdata: Any, rc: int, properties=None):
        self.logger.info("Connected with result code " + str(rc))
        client.subscribe("#")

    def on_message(self, client: Client, userdata: Any, message: MQTTMessage):
        self.logger.info(message.topic)
        msg_json: str = message.payload.decode()
        self.logger.info(msg_json)


if __name__ == "__main__":
    subscriber = Subscriber()
    subscriber.client.loop_forever()
