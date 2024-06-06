import logging
import time
from logging import Logger
from threading import Thread
from typing import Any, List

from injector import Injector

import isar
from isar.apis.api import API
from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.log import setup_loggers
from isar.config.settings import robot_settings, settings
from isar.models.communication.queues.queues import Queues
from isar.modules import get_injector
from isar.services.service_connections.mqtt.mqtt_client import MqttClient
from isar.services.service_connections.mqtt.robot_heartbeat_publisher import (
    RobotHeartbeatPublisher,
)
from isar.services.service_connections.mqtt.robot_info_publisher import (
    RobotInfoPublisher,
)
from isar.state_machine.state_machine import StateMachine, main
from isar.storage.uploader import Uploader
from robot_interface.robot_interface import RobotInterface


def print_setting(
    setting: str = "", value: Any = "", fillchar: str = " ", width: int = 48
):
    separator = ": " if value != "" else ""
    text = setting.ljust(22, fillchar) + separator + str(value)
    print("*", text.ljust(width - 4, fillchar), "*")


def print_startup_info():
    print(
        """
         __   ________   ___        ________
        / /  / ______/  /   |      / ____  /
       / /  / /_____   / /| |     / /___/ /
      / /  /_____  /  / __  |    / __  __/
     / /  ______/ /  / /  | |   / /  | |
    /_/  /_______/  /_/   |_|  /_/   |_|

"""
    )

    WIDTH = 48

    def print_setting(setting: str = "", value: Any = "", fillchar: str = " "):
        separator = ": " if value != "" else ""
        text = setting.ljust(22, fillchar) + separator + str(value)
        print("*", text.ljust(WIDTH - 4, fillchar), "*")

    print("Integration and Supervisory control".center(WIDTH, " "))
    print("of Autonomous Robots".center(WIDTH, " "))
    print()
    print(f"Version: {isar.__version__}\n".center(WIDTH, " "))

    print_setting(fillchar="*")
    print_setting("ISAR settings")
    print_setting(fillchar="-")
    print_setting("Robot package", settings.ROBOT_PACKAGE)
    print_setting("Robot name", settings.ROBOT_NAME)
    print_setting("Run mission stepwise", settings.RUN_MISSION_STEPWISE)
    print_setting("Running on port", settings.API_PORT)
    print_setting("Mission planner", settings.MISSION_PLANNER)
    print_setting("Using local storage", settings.STORAGE_LOCAL_ENABLED)
    print_setting("Using blob storage", settings.STORAGE_BLOB_ENABLED)
    print_setting("Using SLIMM storage", settings.STORAGE_SLIMM_ENABLED)
    print_setting("Plant code", settings.PLANT_CODE)
    print_setting("Plant name", settings.PLANT_NAME)
    print_setting("Plant shortname", settings.PLANT_SHORT_NAME)
    print_setting(fillchar="-")
    print_setting("Robot capabilities", robot_settings.CAPABILITIES)
    print_setting(fillchar="*")
    print()


def start():
    injector: Injector = get_injector()

    keyvault_client = injector.get(Keyvault)
    setup_loggers(keyvault=keyvault_client)
    logger: Logger = logging.getLogger("main")

    print_startup_info()

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

        robot_info_publisher: RobotInfoPublisher = RobotInfoPublisher(
            mqtt_queue=queues.mqtt_queue
        )
        robot_info_thread: Thread = Thread(
            target=robot_info_publisher.run,
            name="ISAR Robot Info Publisher",
            daemon=True,
        )
        threads.append(robot_info_thread)

        robot_heartbeat_publisher: RobotHeartbeatPublisher = RobotHeartbeatPublisher(
            mqtt_queue=queues.mqtt_queue
        )

        robot_heartbeat_thread: Thread = Thread(
            target=robot_heartbeat_publisher.run,
            name="ISAR Robot Heartbeat Publisher",
            daemon=True,
        )
        threads.append(robot_heartbeat_thread)

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
