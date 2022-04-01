import logging
from logging import Logger
from threading import Thread
from typing import List

from injector import Injector

from isar.apis.api import API
from isar.config.log import setup_logger
from isar.config.settings import settings
from isar.models.communication.queues.queues import Queues
from isar.modules import get_injector_modules
from isar.services.service_connections.mqtt.mqtt_client import MqttClient
from isar.state_machine.state_machine import main
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader

if __name__ == "__main__":
    setup_logger()
    logger: Logger = logging.getLogger("main")

    injector_modules, module_config_keys = get_injector_modules()
    injector: Injector = Injector(injector_modules)

    module_config_log = "\n".join(module_config_keys)
    logger.info(f"Loaded the following module configurations:\n{module_config_log}")

    threads: List[Thread] = []

    state_machine_thread: Thread = Thread(
        target=main, name="ISAR State Machine", args=[injector], daemon=True
    )
    threads.append(state_machine_thread)

    uploader: Uploader = Uploader(
        upload_queue=injector.get(Queues).upload_queue,
        storage_handlers=injector.get(List[StorageInterface]),
    )

    uploader_thread: Thread = Thread(
        target=uploader.run, name="ISAR Uploader", daemon=True
    )
    threads.append(uploader_thread)

    if settings.MQTT_ENABLED:
        mqtt_client: MqttClient = MqttClient(mqtt_queue=injector.get(Queues).mqtt_queue)

        mqtt_thread: Thread = Thread(
            target=mqtt_client.run, name="ISAR MQTT Client", daemon=True
        )

        threads.append(mqtt_thread)

    api: API = injector.get(API)
    api_thread: Thread = Thread(target=api.run_app, name="ISAR API", daemon=True)
    threads.append(api_thread)

    for thread in threads:
        thread.start()
        logger.info(f"Started thread: {thread.name}")

    for thread in threads:
        thread.join()
        logger.info(f"Joined thread: {thread.name}")
