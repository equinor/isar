import logging
from logging import Logger
from threading import Thread

import uvicorn
from injector import Injector

from isar.app import create_app
from isar.config import config
from isar.config.log import setup_logger
from isar.modules import get_injector_modules
from isar.state_machine.state_machine import main

if __name__ == "__main__":

    setup_logger()

    injector_modules, module_config_keys = get_injector_modules()
    injector: Injector = Injector(injector_modules)

    state_machine_thread: Thread = Thread(target=main, args=[injector])
    state_machine_thread.start()

    host: str = config.get("fastapi", "run_host")
    port: int = config.getint("fastapi", "run_port")

    app = create_app(
        injector=injector,
        host=host,
        port=port,
    )

    logger: Logger = logging.getLogger("api")

    module_config_log = "\n".join(module_config_keys)
    logger.info(f"Loaded the following module configurations:\n{module_config_log}")

    uvicorn.run(app, port=port, host=host, reload=False, log_config=None)
