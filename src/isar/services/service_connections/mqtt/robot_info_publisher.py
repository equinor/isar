import json
import time
from datetime import datetime, timezone
from queue import Queue

from isar.config.settings import robot_settings, settings
from robot_interface.telemetry.mqtt_client import MqttPublisher
from robot_interface.telemetry.payloads import RobotInfoPayload
from robot_interface.utilities.json_service import EnhancedJSONEncoder


class RobotInfoPublisher:
    def __init__(self, mqtt_queue: Queue):
        self.mqtt_publisher: MqttPublisher = MqttPublisher(mqtt_queue=mqtt_queue)

    def run(self) -> None:
        while True:
            payload: RobotInfoPayload = RobotInfoPayload(
                isar_id=settings.ISAR_ID,
                robot_name=settings.ROBOT_NAME,
                robot_model=robot_settings.ROBOT_MODEL,  # type: ignore
                robot_serial_number=settings.SERIAL_NUMBER,
                robot_asset=settings.PLANT_SHORT_NAME,
                documentation=settings.DOCUMENTATION,
                host=settings.API_HOST_VIEWED_EXTERNALLY,
                port=settings.API_PORT,
                capabilities=robot_settings.CAPABILITIES,
                timestamp=datetime.now(timezone.utc),
            )

            self.mqtt_publisher.publish(
                topic=settings.TOPIC_ISAR_ROBOT_INFO,
                payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            )

            time.sleep(settings.ROBOT_INFO_PUBLISH_INTERVAL)
