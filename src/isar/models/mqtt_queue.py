import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from queue import Empty, Full, Queue

from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from isar.config.settings import settings
from isar.models.status import IsarStatus
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import TASKS
from robot_interface.telemetry.payloads import (
    InterventionNeededPayload,
    IsarStatusPayload,
    MissionAbortedPayload,
    MissionPayload,
    TaskPayload,
)


def props_expiry(seconds: int) -> Properties:
    p = Properties(PacketTypes.PUBLISH)
    p.MessageExpiryInterval = seconds
    return p


@dataclass
class MQTTQueueMessage:
    topic: str
    payload: str
    qos: int
    retain: bool
    properties: Properties | None


class MQTTQueue:
    queue: Queue[MQTTQueueMessage]

    def __init__(self, maxsize: int = 10) -> None:
        self.logger = logging.getLogger("MQTT Queue")
        self.queue = Queue(maxsize=maxsize)
        self.name = "MQTT queue"

    def qsize(self) -> int:
        return self.queue.qsize()

    def empty(self) -> bool:
        return self.queue.empty()

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
        properties: Properties | None = None,
    ) -> None:
        queue_message: MQTTQueueMessage = MQTTQueueMessage(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain,
            properties=properties,
        )
        try:
            self.queue.put(queue_message, timeout=10)
        except Full:
            self.logger.error(
                "MQTT queue filled up before being emptied. Messages lost"
            )

    def get(self, timeout: int = 0) -> MQTTQueueMessage:
        try:
            return self.queue.get(block=timeout != 0, timeout=timeout)
        except Empty:
            return None

    def publish_task_status(self, task: TASKS, mission_id: str | None) -> None:
        """Publishes the task status to the MQTT Broker"""

        error_message: ErrorMessage | None = task.error_message

        payload: TaskPayload = TaskPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=mission_id,
            task_id=task.id if task else None,
            status=task.status if task else None,
            task_type=task.type if task else None,
            error_reason=error_message.error_reason if error_message else None,
            error_description=(
                error_message.error_description if error_message else None
            ),
            timestamp=datetime.now(UTC),
        )

        self.publish(
            topic=settings.TOPIC_ISAR_TASK + f"/{task.id}",
            payload=payload.model_dump_json(),
            qos=1,
            retain=True,
            properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
        )

    def publish_mission_status(
        self,
        mission_id: str,
        mission_status: MissionStatus,
        error_message: ErrorMessage | None,
    ) -> None:
        payload: MissionPayload = MissionPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=mission_id,
            status=mission_status,
            error_reason=error_message.error_reason if error_message else None,
            error_description=(
                error_message.error_description if error_message else None
            ),
            timestamp=datetime.now(UTC),
        )

        self.publish(
            topic=settings.TOPIC_ISAR_MISSION + f"/{mission_id}",
            payload=payload.model_dump_json(),
            qos=1,
            retain=True,
            properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
        )

    def publish_isar_status(self, status: IsarStatus) -> None:
        payload: IsarStatusPayload = IsarStatusPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            status=status,
            timestamp=datetime.now(UTC),
        )

        self.publish(
            topic=settings.TOPIC_ISAR_STATUS,
            payload=payload.model_dump_json(),
            qos=1,
            retain=True,
            properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
        )

    def publish_mission_aborted(
        self, current_mission_id: str | None, reason: str
    ) -> None:
        payload: MissionAbortedPayload = MissionAbortedPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=current_mission_id,
            reason=reason,
            timestamp=datetime.now(UTC),
        )

        self.publish(
            topic=settings.TOPIC_ISAR_MISSION_ABORTED,
            payload=payload.model_dump_json(),
            qos=1,
            retain=True,
            properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
        )

    def publish_intervention_needed(self, error_message: str) -> None:
        """Publishes the intervention needed message to the MQTT Broker"""
        payload: InterventionNeededPayload = InterventionNeededPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            reason=error_message,
            timestamp=datetime.now(UTC),
        )

        self.publish(
            topic=settings.TOPIC_ISAR_INTERVENTION_NEEDED,
            payload=payload.model_dump_json(),
            qos=1,
            retain=True,
            properties=props_expiry(settings.MQTT_MISSION_TASK_AND_STATUS_EXPIRY),
        )
