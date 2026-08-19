import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from logging import Logger
from threading import Thread

from paho.mqtt.properties import Properties

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue, props_expiry
from robot_interface.models.exceptions.robot_exceptions import (
    RobotTelemetryException,
    RobotTelemetryNoUpdateException,
    RobotTelemetryPoseException,
)
from robot_interface.telemetry.payloads import CloudHealthPayload


@dataclass
class TelemetryParameters:
    name: str
    method: Callable[[], str]
    topic: str
    interval: float


class MqttTelemetryPublisher(Thread):
    def __init__(
        self,
        mqtt_queue: MQTTQueue,
        parameters: TelemetryParameters,
    ) -> None:
        self.mqtt_queue: MQTTQueue = mqtt_queue
        self.telemetry_method: Callable[[], str] = parameters.method
        self.topic: str = f"isar/{settings.ISAR_ID}/{parameters.topic}"
        self.interval: float = parameters.interval

        self.logger: Logger = logging.getLogger(f"telemetry - {parameters.name}")

        Thread.__init__(self, name=f"Telemetry thread - {parameters.name}")

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
                payload_str = self.telemetry_method()
                payload_dict = json.loads(payload_str)
                payload_dict["isar_id"] = isar_id
                payload_dict["robot_name"] = robot_name
                payload_dict["timestamp"] = str(datetime.now(UTC))
                payload = json.dumps(payload_dict)
                topic = self.topic
            except RobotTelemetryPoseException, RobotTelemetryNoUpdateException:
                continue
            except RobotTelemetryException:
                payload = json.dumps(
                    CloudHealthPayload(
                        isar_id=isar_id,
                        robot_name=robot_name,
                        timestamp=str(datetime.now(UTC)),
                    )
                )
                topic = f"isar/{isar_id}/cloud_health"
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Unexpected error in MQTT telemetry publisher: {e}")
                continue

            properties: Properties = props_expiry(settings.MQTT_TELEMETRY_EXPIRY)

            self.mqtt_queue.publish(
                topic=topic,
                payload=payload,
                qos=0,
                retain=False,
                properties=properties,
            )
