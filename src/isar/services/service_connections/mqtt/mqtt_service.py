import json
import logging
import time
from logging import Logger
from typing import Any, Optional

from paho.mqtt.client import Client

from isar.config import config
from isar.models.communication.messages import StartMessage, StopMessage
from isar.models.mission import Mission
from isar.services.service_connections.mqtt.mqtt_service_interface import (
    MQTTConnectionError,
    MQTTServiceInterface,
)
from isar.services.utilities.json_service import EnhancedJSONEncoder
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.step import Step


class MQTTService(MQTTServiceInterface):
    def __init__(
        self,
        host: str = config.get("mqtt", "host"),
        port: str = config.getint("mqtt", "port"),
        username: str = config.get("mqtt", "username"),
        password: str = config.get("mqtt", "password"),
        client_id: str = config.get("mqtt", "client_id"),
    ):
        self.logger: Logger = logging.getLogger("mqtt")
        self.logger.info("Creating MQTT Client")
        self.mission_status_topic: str = config.get(
            "mqtt_topics", "mission_status_topic"
        )
        self.mission_in_progress_topic: str = config.get(
            "mqtt_topics", "mission_in_progress_topic"
        )
        self.current_mission_instance_id_topic: str = config.get(
            "mqtt_topics", "current_mission_instance_id_topic"
        )
        self.current_mission_step_topic: str = config.get(
            "mqtt_topics", "current_mission_step_topic"
        )
        self.mission_schedule_topic: str = config.get(
            "mqtt_topics", "mission_schedule_topic"
        )
        self.current_state_topic: str = config.get("mqtt_topics", "current_state_topic")

        self.start_mission_topic: str = config.get("mqtt_topics", "start_mission_topic")
        self.start_mission_ack_topic: str = config.get(
            "mqtt_topics", "start_mission_ack_topic"
        )

        self.stop_mission_topic: str = config.get("mqtt_topics", "stop_mission_topic")
        self.stop_mission_ack_topic: str = config.get(
            "mqtt_topics", "stop_mission_ack_topic"
        )

        self.connection_timeout: float = config.getfloat("mqtt", "connection_timeout")
        self.connection_sleep: float = config.getfloat("mqtt", "connection_sleep")

        self.host: str = host
        self.port: str = port
        self.client_id: str = client_id

        self.mqtt_client: Client = Client(client_id=self.client_id)
        self.mqtt_client.username_pw_set(username=username, password=password)

        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect

        self.disconnection_time: Optional[float] = None

        self._connect()

    def _connect(self) -> None:
        try:
            self.mqtt_client.connect(host=self.host, port=self.port, keepalive=60)
        except ConnectionRefusedError:
            self.logger.error("Error connecting to mqtt_broker")

        self.mqtt_client.loop_start()
        start_time: float = time.time()
        while not self.mqtt_client.is_connected():
            if time.time() - start_time > self.connection_timeout:
                raise MQTTConnectionError
            time.sleep(self.connection_sleep)

    def _on_connect(self, mqttc: Client, userdata: Any, flags: dict, rc: int) -> None:
        self.logger.info("Connected to MQTT-broker with result code: " + str(rc))
        self.disconnection_time = None

    def _on_disconnect(self, client: Client, userdata: Any, rc: int) -> None:
        self.logger.info("Disconnected from MQTT-broker with result code: " + str(rc))
        if not self.disconnection_time:
            self.disconnection_time = time.time()

    def is_connected(self) -> bool:
        return self.mqtt_client.is_connected()

    def time_since_disconnect(self) -> float:
        if not self.disconnection_time:
            return 0.0
        return time.time() - self.disconnection_time

    def publish_mission_status_message(self, status: MissionStatus) -> None:
        self.mqtt_client.publish(topic=self.mission_status_topic, payload=status)

    def publish_mission_in_progress_message(self, mission_in_progress: bool) -> None:
        self.mqtt_client.publish(
            topic=self.mission_in_progress_topic, payload=mission_in_progress
        )

    def publish_current_mission_instance_id(
        self, mission_instance_id: Optional[int]
    ) -> None:
        self.mqtt_client.publish(
            topic=self.current_mission_instance_id_topic,
            payload=mission_instance_id,
        )

    def publish_current_mission_step(self, mission_step: Optional[Step]) -> None:
        self.mqtt_client.publish(
            topic=self.current_mission_step_topic,
            payload=json.dumps(mission_step, cls=EnhancedJSONEncoder),
        )

    def publish_mission_schedule(self, mission_schedule: Mission) -> None:
        self.mqtt_client.publish(
            topic=self.mission_schedule_topic,
            payload=json.dumps(mission_schedule, cls=EnhancedJSONEncoder),
        )

    def publish_current_state(self, state: States) -> None:
        self.mqtt_client.publish(self.current_state_topic, state)

    def publish_start_mission(self, mission: Mission) -> None:
        self.mqtt_client.publish(
            topic=self.start_mission_topic,
            payload=json.dumps(mission, cls=EnhancedJSONEncoder),
        )

    def publish_start_mission_ack(self, start_mission_message: StartMessage) -> None:
        self.mqtt_client.publish(
            topic=self.start_mission_ack_topic,
            payload=json.dumps(start_mission_message.__dict__),
        )

    def publish_stop_mission(self) -> None:
        self.mqtt_client.publish(topic=self.stop_mission_topic, payload="True")

    def publish_stop_mission_ack(self, stop_mission_message: StopMessage) -> None:
        self.mqtt_client.publish(
            topic=self.stop_mission_ack_topic,
            payload=json.dumps(stop_mission_message.__dict__),
        )

    def subscribe_start_mission(self, callback=None) -> None:
        self.mqtt_client.subscribe(self.start_mission_topic)
        if callback:
            self.mqtt_client.message_callback_add(self.start_mission_topic, callback)

    def subscribe_start_mission_ack(self, callback=None) -> None:
        self.mqtt_client.subscribe(self.start_mission_ack_topic)
        if callback:
            self.mqtt_client.message_callback_add(
                self.start_mission_ack_topic, callback=callback
            )

    def subscribe_stop_mission(self, callback=None) -> None:
        self.mqtt_client.subscribe(self.stop_mission_topic)
        if callback is not None:
            self.mqtt_client.message_callback_add(self.stop_mission_topic, callback)

    def subscribe_stop_mission_ack(self, callback=None) -> None:
        self.mqtt_client.subscribe(self.stop_mission_ack_topic)
        if callback:
            self.mqtt_client.message_callback_add(
                self.stop_mission_ack_topic, callback=callback
            )
