import json
import logging
import time
from http import HTTPStatus
from logging import Logger
from threading import Lock
from typing import Any, Optional, Tuple

from injector import inject
from paho.mqtt.client import Client, MQTTMessage

from isar.config import config
from isar.models.communication.messages import (
    StartMessage,
    StartMissionMessages,
    StopMessage,
    StopMissionMessages,
)
from isar.models.mission import Mission
from isar.services.service_connections.mqtt.mqtt_service_interface import (
    MQTTServiceInterface,
)
from isar.services.utilities.json_service import StartMessageDecoder, StopMessageDecoder


class SchedulingUtilities:
    """
    Contains utility functions for scheduling missions from the API. The class handles required thread communication
    through MQTT to the state machine.
    """

    @inject
    def __init__(
        self,
        mqtt_service: MQTTServiceInterface,
        ack_timeout: float = config.getfloat("mqtt", "ack_timeout"),
    ):
        self.ack_timeout: float = ack_timeout
        self.logger: Logger = logging.getLogger("api")
        self.mqtt_service: MQTTServiceInterface = mqtt_service
        self.mqtt_service.subscribe_start_mission_ack(
            self.on_start_mission_ack_callback
        )
        self.mqtt_service.subscribe_stop_mission_ack(self.on_stop_mission_ack_callback)
        self.start_message_ack: Optional[StartMessage] = None
        self.stop_message_ack: Optional[StopMessage] = None

    def start_mission(self, mission: Mission) -> Tuple[StartMessage, int]:
        """
        Starts a mission by communicating with the state machine thread through MQTT.
        :param mission: A Mission containing the mission steps to be started.
        :return: (message, status_code) is returned indicating the success and cause of the operation.
        """
        self.mqtt_service.publish_start_mission(mission)
        start_message: StartMessage = self.wait_on_start_ack()
        self.start_message_ack = None

        if not start_message.started:
            return start_message, HTTPStatus.CONFLICT

        return start_message, HTTPStatus.OK

    def stop_mission(self) -> Tuple[StopMessage, int]:

        self.mqtt_service.publish_stop_mission()
        stop_message: StopMessage = self.wait_on_stop_ack()
        self.stop_message_ack = None

        if not stop_message.stopped:
            return stop_message, HTTPStatus.CONFLICT

        return stop_message, HTTPStatus.OK

    def on_start_mission_ack_callback(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        msg_json: str = message.payload.decode()
        start_message: StartMessage = json.loads(msg_json, cls=StartMessageDecoder)
        self.start_message_ack = start_message

    def on_stop_mission_ack_callback(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        msg_json: str = message.payload.decode()
        stop_message: StopMessage = json.loads(msg_json, cls=StopMessageDecoder)
        self.stop_message_ack = stop_message

    def wait_on_start_ack(self) -> StartMessage:
        start_time: float = time.time()
        while True:
            if self.start_message_ack:
                return self.start_message_ack
            if time.time() - start_time > self.ack_timeout:
                return StartMissionMessages.ack_timeout()
            time.sleep(0.1)

    def wait_on_stop_ack(self) -> StopMessage:
        start_time: float = time.time()
        while True:
            if self.stop_message_ack:
                return self.stop_message_ack
            if time.time() - start_time > self.ack_timeout:
                return StopMissionMessages.ack_timeout()
            time.sleep(0.1)
