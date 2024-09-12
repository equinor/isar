import json
import time
from datetime import datetime, timezone
from queue import Queue

from isar.config.settings import settings
from robot_interface.telemetry.mqtt_client import MqttPublisher
from robot_interface.telemetry.payloads import RobotHeartbeatPayload
from robot_interface.utilities.json_service import EnhancedJSONEncoder


class RobotHeartbeatPublisher:
    def __init__(self, mqtt_queue: Queue):
        self.mqtt_publisher: MqttPublisher = MqttPublisher(mqtt_queue=mqtt_queue)

    def run(self) -> None:
        while True:
            payload: RobotHeartbeatPayload = RobotHeartbeatPayload(
                isar_id=settings.ISAR_ID,
                robot_name=settings.ROBOT_NAME,
                timestamp=datetime.now(timezone.utc),
            )

            self.mqtt_publisher.publish(
                topic=settings.TOPIC_ISAR_ROBOT_HEARTBEAT,
                payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            )

            time.sleep(settings.ROBOT_HEARTBEAT_PUBLISH_INTERVAL)
