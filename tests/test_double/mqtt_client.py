from typing import Any

from paho.mqtt.properties import Properties

from robot_interface.telemetry.mqtt_client import MqttClientInterface


class MqttClientDummy(MqttClientInterface):
    def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = 0,
        retain: bool = False,
        properties: Properties = None,
    ) -> None:
        pass
