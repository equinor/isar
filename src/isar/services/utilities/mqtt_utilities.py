from datetime import datetime, timezone
from typing import Optional

from isar.config.settings import settings
from isar.models.status import IsarStatus
from isar.services.service_connections.mqtt.mqtt_client import props_expiry
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import TASKS
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.telemetry.payloads import (
    IsarStatusPayload,
    MissionPayload,
    TaskPayload,
)


def publish_task_status(
    mqtt_publisher: MqttClientInterface, task: TASKS, mission_id: Optional[str]
) -> None:
    """Publishes the task status to the MQTT Broker"""

    error_message: Optional[ErrorMessage] = None
    if task:
        if task.error_message:
            error_message = task.error_message

    payload: TaskPayload = TaskPayload(
        isar_id=settings.ISAR_ID,
        robot_name=settings.ROBOT_NAME,
        mission_id=mission_id,
        task_id=task.id if task else None,
        status=task.status if task else None,
        task_type=task.type if task else None,
        error_reason=error_message.error_reason if error_message else None,
        error_description=(error_message.error_description if error_message else None),
        timestamp=datetime.now(timezone.utc),
    )

    mqtt_publisher.publish(
        topic=settings.TOPIC_ISAR_TASK + f"/{task.id}",
        payload=payload.model_dump_json(),
        qos=1,
        retain=False,
        properties=props_expiry(settings.MQTT_MISSION_AND_TASK_EXPIRY),
    )


def publish_mission_status(
    mqtt_publisher: MqttClientInterface,
    mission_id: str,
    mission_status: MissionStatus,
    error_message: Optional[ErrorMessage],
) -> None:
    if not mqtt_publisher:
        return

    payload: MissionPayload = MissionPayload(
        isar_id=settings.ISAR_ID,
        robot_name=settings.ROBOT_NAME,
        mission_id=mission_id,
        status=mission_status,
        error_reason=error_message.error_reason if error_message else None,
        error_description=(error_message.error_description if error_message else None),
        timestamp=datetime.now(timezone.utc),
    )

    mqtt_publisher.publish(
        topic=settings.TOPIC_ISAR_MISSION + f"/{mission_id}",
        payload=payload.model_dump_json(),
        qos=1,
        retain=False,
        properties=props_expiry(settings.MQTT_MISSION_AND_TASK_EXPIRY),
    )


def publish_isar_status(
    mqtt_publisher: MqttClientInterface, status: IsarStatus
) -> None:
    payload: IsarStatusPayload = IsarStatusPayload(
        isar_id=settings.ISAR_ID,
        robot_name=settings.ROBOT_NAME,
        status=status,
        timestamp=datetime.now(timezone.utc),
    )

    mqtt_publisher.publish(
        topic=settings.TOPIC_ISAR_STATUS,
        payload=payload.model_dump_json(),
        qos=1,
        retain=False,
        properties=props_expiry(settings.MQTT_MISSION_AND_TASK_EXPIRY),
    )
