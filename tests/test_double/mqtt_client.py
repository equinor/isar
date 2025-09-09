from threading import Lock
from typing import Any, Dict, List, Optional

from robot_interface.telemetry.mqtt_client import MqttClientInterface


class MqttPublisherFake(MqttClientInterface):
    def __init__(self) -> None:
        self._lock = Lock()
        self.published: List[Dict[str, Any]] = []

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
        properties: Optional[Any] = None,
    ) -> None:
        with self._lock:
            self.published.append(
                {
                    "topic": topic,
                    "payload": payload,
                    "qos": qos,
                    "retain": retain,
                    "properties": properties,
                }
            )

    def last(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.published[-1] if self.published else None

    def count(self) -> int:
        with self._lock:
            return len(self.published)
