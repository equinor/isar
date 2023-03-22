import logging
import time
from logging import Logger
from threading import Thread
from typing import List

from injector import Injector

from isar.apis.api import API
from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.log import setup_loggers
from isar.config.settings import settings
from isar.models.communication.queues.queues import Queues
from isar.modules import get_injector
from isar.services.service_connections.mqtt.mqtt_client import MqttClient
from isar.services.service_connections.mqtt.robot_info_publisher import (
    RobotInfoPublisher,
)
from isar.services.service_connections.mqtt.robot_status_publisher import (
    RobotStatusPublisher,
)
from isar.state_machine.state_machine import StateMachine, main
from isar.storage.uploader import Uploader
from robot_interface.robot_interface import RobotInterface

if __name__ == "__main__":
    injector: Injector = get_injector()

    keyvault_client = injector.get(Keyvault)
    setup_loggers(keyvault=keyvault_client)
    logger: Logger = logging.getLogger("main")

    state_machine: StateMachine = injector.get(StateMachine)
    uploader: Uploader = injector.get(Uploader)
    robot: RobotInterface = injector.get(RobotInterface)
    queues: Queues = injector.get(Queues)

    threads: List[Thread] = []

    state_machine_thread: Thread = Thread(
        target=main, name="ISAR State Machine", args=[state_machine], daemon=True
    )
    threads.append(state_machine_thread)

    uploader_thread: Thread = Thread(
        target=uploader.run, name="ISAR Uploader", daemon=True
    )
    threads.append(uploader_thread)

    if settings.MQTT_ENABLED:
        mqtt_client: MqttClient = MqttClient(mqtt_queue=queues.mqtt_queue)

        mqtt_thread: Thread = Thread(
            target=mqtt_client.run, name="ISAR MQTT Client", daemon=True
        )
        threads.append(mqtt_thread)

        robot_status_publisher: RobotStatusPublisher = RobotStatusPublisher(
            mqtt_queue=queues.mqtt_queue, robot=robot, state_machine=state_machine
        )
        robot_status_thread: Thread = Thread(
            target=robot_status_publisher.run,
            name="ISAR Robot Status Publisher",
            daemon=True,
        )
        threads.append(robot_status_thread)

        robot_info_publisher: RobotInfoPublisher = RobotInfoPublisher(
            mqtt_queue=queues.mqtt_queue
        )
        robot_info_thread: Thread = Thread(
            target=robot_info_publisher.run,
            name="ISAR Robot Info Publisher",
            daemon=True,
        )
        threads.append(robot_info_thread)

        publishers: List[Thread] = robot.get_telemetry_publishers(
            queue=queues.mqtt_queue,
            robot_name=settings.ROBOT_NAME,
            isar_id=settings.ISAR_ID,
        )
        if publishers:
            threads.extend(publishers)

    api: API = injector.get(API)
    api_thread: Thread = Thread(target=api.run_app, name="ISAR API", daemon=True)
    threads.append(api_thread)

    for thread in threads:
        thread.start()
        logger.info(f"Started thread: {thread.name}")

    while True:
        for thread in threads:
            if not thread.is_alive():
                logger.critical("Thread '%s' failed - ISAR shutting down", thread.name)
                exit(1)
        time.sleep(state_machine.sleep_time)
