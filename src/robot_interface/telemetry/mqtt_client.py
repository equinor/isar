import json
import time
from abc import ABCMeta, abstractmethod
from datetime import datetime, timezone
from queue import Queue
from typing import Callable, Tuple

from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    RobotTelemetryException,
    RobotTelemetryNoUpdateException,
    RobotTelemetryPoseException,
)
from robot_interface.telemetry.payloads import CloudHealthPayload
from robot_interface.utilities.json_service import EnhancedJSONEncoder


def props_expiry(seconds: int) -> Properties:
    p = Properties(PacketTypes.PUBLISH)
    p.MessageExpiryInterval = seconds
    return p


class MqttClientInterface(metaclass=ABCMeta):
    @abstractmethod
    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
        properties: Properties = None,
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
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
        properties: Properties = None,
    ) -> None:
        queue_message: Tuple[str, str, int, bool, Properties] = (
            topic,
            payload,
            qos,
            retain,
            properties,
        )
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
        properties: Properties = None,
    ) -> None:
        self.mqtt_queue: Queue = mqtt_queue
        self.telemetry_method: Callable = telemetry_method
        self.topic: str = topic
        self.interval: float = interval
        self.qos: int = qos
        self.retain: bool = retain
        self.properties: Properties = properties

    def run(self, isar_id: str, robot_name: str) -> None:
        self.cloud_health_topic: str = f"isar/{isar_id}/cloud_health"
        self.battery_topic: str = f"isar/{isar_id}/battery"
        self.pose_topic: str = f"isar/{isar_id}/pose"
        self.pressure_topic: str = f"isar/{isar_id}/pressure"
        topic: str
        payload: str

        while True:
            try:
                payload = self.telemetry_method(isar_id=isar_id, robot_name=robot_name)
                topic = self.topic
            except (RobotTelemetryPoseException, RobotTelemetryNoUpdateException):
                time.sleep(self.interval)
                continue
            except RobotTelemetryException:
                payload = json.dumps(
                    CloudHealthPayload(isar_id, robot_name, datetime.now(timezone.utc)),
                    cls=EnhancedJSONEncoder,
                )
                topic = self.cloud_health_topic

            publish_properties = self.properties

            if topic in (
                self.battery_topic,
                self.pose_topic,
                self.pressure_topic,
            ):
                publish_properties = props_expiry(settings.MQTT_TELEMETRY_EXPIRY)

            self.publish(
                topic=topic,
                payload=payload,
                qos=self.qos,
                retain=self.retain,
                properties=publish_properties,
            )
            time.sleep(self.interval)

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
        properties: Properties = None,
    ) -> None:
        queue_message: Tuple[str, str, int, bool, Properties] = (
            topic,
            payload,
            qos,
            retain,
            properties,
        )
        self.mqtt_queue.put(queue_message)
