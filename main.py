import logging
from logging import Logger
from threading import Thread
from typing import List

from injector import Injector, Module

from isar import create_app
from isar.config import config
from isar.modules import get_injector_modules
from isar.state_machine.state_machine import main

if __name__ == "__main__":

    injector_modules, module_config_keys = get_injector_modules()
    injector: Injector = Injector(injector_modules)

    state_machine_thread: Thread = Thread(target=main, args=[injector])
    state_machine_thread.start()

    app = create_app(injector=injector)

    host = config.get("environment", "flask_run_host")
    port = config.getint("environment", "flask_run_port")

    logger: Logger = logging.getLogger("api")

    module_config_log = "\n".join(module_config_keys)
    logger.info(f"Loaded the following module configurations:\n{module_config_log}")

    app.run(host, port, use_reloader=False)
