import time
from abc import ABCMeta, abstractmethod
from queue import Queue
from typing import Callable, Tuple

from robot_interface.models.exceptions.robot_exceptions import (
    RobotInvalidTelemetryException,
)


class MqttClientInterface(metaclass=ABCMeta):
    @abstractmethod
    def publish(
        self, topic: str, payload: str, qos: int = 0, retain: bool = False
    ) -> None:
        """
        Parameters
        ----------
        topic : string
            MQTT topic to publish to
        payload : string
            Payload to send to publish on the topic
        qos : integer
            Quality of Service
        retain : boolean
            Retain on topic

        Returns
        -------

        """
        pass


class MqttPublisher(MqttClientInterface):
    def __init__(self, mqtt_queue: Queue) -> None:
        self.mqtt_queue: Queue = mqtt_queue

    def publish(
        self, topic: str, payload: str, qos: int = 0, retain: bool = False
    ) -> None:
        queue_message: Tuple[str, str, int, bool] = (topic, payload, qos, retain)
        self.mqtt_queue.put(queue_message)


class MqttTelemetryPublisher(MqttClientInterface):
    def __init__(
        self,
        mqtt_queue: Queue,
        telemetry_method: Callable,
        topic: str,
        interval: float,
        qos: int = 0,
        retain: bool = False,
    ) -> None:
        self.mqtt_queue: Queue = mqtt_queue
        self.telemetry_method: Callable = telemetry_method
        self.topic: str = topic
        self.interval: float = interval
        self.qos: int = qos
        self.retain: bool = retain

    def run(self, robot_id: str) -> None:
        while True:
            try:
                payload: str = self.telemetry_method(robot_id)
            except RobotInvalidTelemetryException:
                continue

            self.publish(
                topic=self.topic, payload=payload, qos=self.qos, retain=self.retain
            )
            time.sleep(self.interval)

    def publish(
        self, topic: str, payload: str, qos: int = 0, retain: bool = False
    ) -> None:
        queue_message: Tuple[str, str, int, bool] = (topic, payload, qos, retain)
        self.mqtt_queue.put(queue_message)
