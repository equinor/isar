from typing import Any

from robot_interface.telemetry.mqtt_client import MqttClientInterface


class MqttClientMock(MqttClientInterface):
    def publish(
        self, topic: str, payload: Any, qos: int = 0, retain: bool = False
    ) -> None:
        pass
