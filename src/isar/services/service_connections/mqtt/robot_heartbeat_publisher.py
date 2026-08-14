import time
from datetime import UTC, datetime

from isar.config.settings import settings
from isar.models.mqtt_queue import MQTTQueue
from robot_interface.telemetry.mqtt_client import props_expiry
from robot_interface.telemetry.payloads import RobotHeartbeatPayload


class RobotHeartbeatPublisher:
    def __init__(self, mqtt_queue: MQTTQueue):
        self.mqtt_queue: MQTTQueue = mqtt_queue

    def run(self) -> None:
        while True:
            payload: RobotHeartbeatPayload = RobotHeartbeatPayload(
                isar_id=settings.ISAR_ID,
                robot_name=settings.ROBOT_NAME,
                timestamp=datetime.now(UTC),
            )

            self.mqtt_queue.publish(
                topic=settings.TOPIC_ISAR_ROBOT_HEARTBEAT,
                payload=payload.model_dump_json(),
                retain=False,
                properties=props_expiry(settings.MQTT_ROBOT_HEARTBEAT_EXPIRY),
            )

            time.sleep(settings.ROBOT_HEARTBEAT_PUBLISH_INTERVAL)
