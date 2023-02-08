import json
import time
from datetime import datetime
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
                video_streams=settings.VIDEO_STREAMS,
                host=settings.API_HOST_VIEWED_EXTERNALLY,
                port=settings.API_PORT,
                timestamp=datetime.utcnow(),
            )

            self.mqtt_publisher.publish(
                topic=settings.TOPIC_ISAR_ROBOT_INFO,
                payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            )

            time.sleep(settings.ROBOT_INFO_PUBLISH_INTERVAL)
