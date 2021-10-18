from threading import Thread
from typing import List

from injector import Injector, Module

from isar import create_app
from isar.config import config
from isar.modules import modules
from isar.state_machine.state_machine import main


def get_injector_modules() -> List[Module]:
    injector_modules: List[Module] = []

    module_config: dict = dict(config.items("modules"))

    for module_key, module in modules.items():

        injector_modules.append(
            module[
                "default"
                if not module_key in module_config
                else module_config[module_key]
            ]
        )

    return injector_modules


if __name__ == "__main__":

    injector_modules: List[Module] = get_injector_modules()
    injector: Injector = Injector(injector_modules)

    state_machine_thread: Thread = Thread(target=main, args=[injector])
    state_machine_thread.start()

    app = create_app(injector=injector)

    host = config.get("environment", "flask_run_host")
    port = config.getint("environment", "flask_run_port")

    app.run(host, port, use_reloader=False)
