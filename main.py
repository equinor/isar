import logging
from logging import Logger
from threading import Thread
from typing import List

from injector import Injector

from isar.apis.api import API
from isar.config import config
from isar.config.log import setup_logger
from isar.models.communication.queues.queues import Queues
from isar.modules import get_injector_modules
from isar.state_machine.state_machine import main
from isar.storage.storage_interface import StorageInterface
from isar.storage.uploader import Uploader

if __name__ == "__main__":
    setup_logger()

    injector_modules, module_config_keys = get_injector_modules()
    injector: Injector = Injector(injector_modules)

    state_machine_thread: Thread = Thread(target=main, args=[injector])
    state_machine_thread.start()

    uploader: Uploader = Uploader(
        upload_queue=injector.get(Queues).upload_queue,
        storage_handlers=injector.get(List[StorageInterface]),
    )

    uploader_thread: Thread = Thread(target=uploader.run)
    uploader_thread.start()

    host: str = config.get("DEFAULT", "api_host")
    port: int = config.getint("DEFAULT", "api_port")

    logger: Logger = logging.getLogger("api")

    module_config_log = "\n".join(module_config_keys)
    logger.info(f"Loaded the following module configurations:\n{module_config_log}")

    injector.get(API).run_app()
