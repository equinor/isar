import json
import logging
import time
from datetime import datetime
from logging import Logger
from queue import Queue
from threading import Thread
from typing import Optional

from isar.config.settings import settings
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import (
    RobotAPIException,
    RobotCommunicationException,
    RobotException,
)
from robot_interface.models.mission.status import RobotStatus
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttPublisher
from robot_interface.telemetry.payloads import RobotStatusPayload
from robot_interface.utilities.json_service import EnhancedJSONEncoder


class RobotStatusPublisher:
    def __init__(
        self, mqtt_queue: Queue, robot: RobotInterface, state_machine: StateMachine
    ):
        self.mqtt_publisher: MqttPublisher = MqttPublisher(mqtt_queue=mqtt_queue)
        self.robot: RobotInterface = robot
        self.state_machine: StateMachine = state_machine

    def _get_combined_robot_status(
        self, robot_status: RobotStatus, current_state: States
    ) -> RobotStatus:
        if robot_status == RobotStatus.Offline:
            return RobotStatus.Offline
        elif current_state == States.Idle and robot_status == RobotStatus.Available:
            return RobotStatus.Available
        elif robot_status == RobotStatus.Blocked:
            return RobotStatus.Blocked
        elif current_state != States.Idle or robot_status == RobotStatus.Busy:
            return RobotStatus.Busy
        return None

    def run(self) -> None:
        robot_status_monitor: RobotStatusMonitor = RobotStatusMonitor(robot=self.robot)
        robot_status_thread: Thread = Thread(
            target=robot_status_monitor.run,
            name="Robot Status Monitor",
            daemon=True,
        )
        robot_status_thread.start()

        previous_robot_status: Optional[RobotStatus] = None

        while True:
            time.sleep(settings.ROBOT_STATUS_PUBLISH_INTERVAL)

            combined_status: RobotStatus = self._get_combined_robot_status(
                robot_status=robot_status_monitor.robot_status,
                current_state=self.state_machine.current_state,
            )

            if previous_robot_status:
                if previous_robot_status == combined_status:
                    continue

            payload: RobotStatusPayload = RobotStatusPayload(
                isar_id=settings.ISAR_ID,
                robot_name=settings.ROBOT_NAME,
                robot_status=combined_status,
                previous_robot_status=previous_robot_status,
                current_isar_state=self.state_machine.current_state,
                current_mission_id=(
                    self.state_machine.current_mission.id
                    if self.state_machine.current_mission
                    else None
                ),
                current_task_id=(
                    self.state_machine.current_task.id
                    if self.state_machine.current_task
                    else None
                ),
                current_step_id=(
                    self.state_machine.current_step.id
                    if self.state_machine.current_step
                    else None
                ),
                timestamp=datetime.utcnow(),
            )

            self.mqtt_publisher.publish(
                topic=settings.TOPIC_ISAR_ROBOT_STATUS,
                payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            )

            previous_robot_status = combined_status


class RobotStatusMonitor:
    def __init__(self, robot: RobotInterface):
        self.robot: RobotInterface = robot
        self.robot_status: RobotStatus = RobotStatus.Offline
        self.logger: Logger = logging.getLogger("robot_status_monitor")

    def run(self) -> None:
        while True:
            try:
                self.robot_status = self.robot.robot_status()
            except (
                RobotCommunicationException,
                RobotAPIException,
                RobotException,
            ) as e:
                self.logger.error(
                    f"Failed to get robot status because: {e.error_description}"
                )
            time.sleep(settings.ROBOT_API_STATUS_POLL_INTERVAL)
