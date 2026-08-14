import json
import logging
import time
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from logging import Logger
from queue import Queue
from threading import Thread

from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    RobotTelemetryException,
    RobotTelemetryNoUpdateException,
    RobotTelemetryPoseException,
)
from robot_interface.telemetry.payloads import CloudHealthPayload

MQTTQueueType = tuple[str, str, int, bool, Properties | None]


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
        properties: Properties | None = None,
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


class MqttPublisher(MqttClientInterface):
    def __init__(self, mqtt_queue: Queue[MQTTQueueType]) -> None:
        self.mqtt_queue: Queue[MQTTQueueType] = mqtt_queue

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> None:
        queue_message: tuple[str, str, int, bool, Properties | None] = (
            topic,
            payload,
            qos,
            retain,
            properties,
        )
        self.mqtt_queue.put(queue_message)


class MqttTelemetryPublisher(Thread):
    def __init__(
        self,
        name: str,
        mqtt_queue: Queue[MQTTQueueType],
        telemetry_method: Callable,
        topic: str,
        interval: float,
        should_expire: bool,
    ) -> None:
        self.mqtt_queue: Queue[MQTTQueueType] = mqtt_queue
        self.telemetry_method: Callable = telemetry_method
        self.topic: str = topic
        self.interval: float = interval
        self.should_expire: bool = should_expire

        self.logger: Logger = logging.getLogger("telemetry")

        Thread.__init__(self, name=f"Telemetry thread - {name}")

    def stop(self) -> None:
        return

    def run(self) -> None:
        robot_name = settings.ROBOT_NAME
        isar_id = settings.ISAR_ID
        topic: str
        payload: str

        while True:
            time.sleep(self.interval)
            try:
                payload = self.telemetry_method()
                topic = self.topic
            except RobotTelemetryPoseException, RobotTelemetryNoUpdateException:
                continue
            except RobotTelemetryException:
                payload = json.dumps(
                    CloudHealthPayload(
                        isar_id=isar_id,
                        robot_name=robot_name,
                        timestamp=datetime.now(UTC),
                    )
                )
                topic = f"isar/{isar_id}/cloud_health"
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Unexpected error in MQTT telemetry publisher: {e}")
                continue

            properties: Properties | None = None
            if self.should_expire:
                properties = props_expiry(settings.MQTT_TELEMETRY_EXPIRY)

            queue_message: MQTTQueueType = (
                topic,
                payload,
                0,
                False,
                properties,
            )
            self.mqtt_queue.put(queue_message)
