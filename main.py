import logging
from logging import Logger
from threading import Thread
from typing import List

from dotenv import load_dotenv
from injector import Injector

from isar.apis.api import API
from isar.config.log import setup_logger
from isar.config.settings import settings
from isar.models.communication.queues.queues import Queues
from isar.modules import get_injector
from isar.services.service_connections.mqtt.mqtt_client import MqttClient
from isar.state_machine.state_machine import main
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader
from robot_interface.robot_interface import RobotInterface

if __name__ == "__main__":
    load_dotenv()

    setup_logger()
    logger: Logger = logging.getLogger("main")

    injector: Injector = get_injector()

    robot: RobotInterface = injector.get(RobotInterface)
    queues: Queues = injector.get(Queues)

    threads: List[Thread] = []

    state_machine_thread: Thread = Thread(
        target=main, name="ISAR State Machine", args=[injector], daemon=True
    )
    threads.append(state_machine_thread)

    uploader: Uploader = Uploader(
        upload_queue=queues.upload_queue,
        storage_handlers=injector.get(List[StorageInterface]),
    )

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

        publishers: List[Thread] = robot.get_telemetry_publishers(
            queue=queues.mqtt_queue, robot_id=settings.ROBOT_ID
        )
        threads.extend(publishers)

    api: API = injector.get(API)
    api_thread: Thread = Thread(target=api.run_app, name="ISAR API", daemon=True)
    threads.append(api_thread)

    for thread in threads:
        thread.start()
        logger.info(f"Started thread: {thread.name}")

    for thread in threads:
        thread.join()
        logger.info(f"Joined thread: {thread.name}")
