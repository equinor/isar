from typing import Any

from isar.services.service_connections.mqtt.mqtt_client import MqttClientInterface


class MqttClientMock(MqttClientInterface):
    def publish(
        self, topic: str, payload: Any, qos: int = 0, retain: bool = False
    ) -> None:
        pass
