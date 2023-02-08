import json
import time
from datetime import datetime
from queue import Queue
from threading import Thread

from isar.config.settings import settings
from isar.state_machine.state_machine import StateMachine
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

    def run(self) -> None:
        robot_status_monitor: RobotStatusMonitor = RobotStatusMonitor(robot=self.robot)
        robot_status_thread: Thread = Thread(
            target=robot_status_monitor.run,
            name="Robot Status Monitor",
            daemon=True,
        )
        robot_status_thread.start()

        while True:
            payload: RobotStatusPayload = RobotStatusPayload(
                robot_name=settings.ROBOT_ID,
                robot_status=robot_status_monitor.robot_status,
                current_isar_state=self.state_machine.current_state,
                current_mission_id=self.state_machine.current_mission.id
                if self.state_machine.current_mission
                else None,
                current_task_id=self.state_machine.current_task.id
                if self.state_machine.current_task
                else None,
                current_step_id=self.state_machine.current_step.id
                if self.state_machine.current_step
                else None,
                timestamp=datetime.utcnow(),
            )

            self.mqtt_publisher.publish(
                topic=settings.TOPIC_ISAR_ROBOT_STATUS,
                payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            )

            time.sleep(settings.ROBOT_STATUS_PUBLISH_INTERVAL)


class RobotStatusMonitor:
    def __init__(self, robot: RobotInterface):
        self.robot = robot
        self.robot_status: RobotStatus = RobotStatus.Offline

    def run(self) -> None:
        while True:
            self.robot_status = self.robot.robot_status()
            time.sleep(settings.ROBOT_API_STATUS_POLL_INTERVAL)
