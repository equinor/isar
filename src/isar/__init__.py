import logging
import logging.config
from threading import Thread

import yaml
from flask import Flask
from flask_cors import CORS
from flask_injector import FlaskInjector
from injector import Injector
from isar.apis import api_blueprint
from isar.config import config
from isar.services.utilities.json_service import EnhancedJSONEncoder
from isar.state_machine.state_machine import main

from .modules import (
    CoordinateModule,
    QueuesModule,
    ReaderModule,
    RequestHandlerModule,
    RobotModule,
    SchedulerModule,
    ServiceModule,
    StateMachineModule,
    StorageModule,
    TelemetryModule,
    UtilitiesModule,
)


def create_app(test_config=False):
    logging.config.dictConfig(yaml.safe_load(open(f"./src/isar/config/logging.conf")))
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
        config.get("logging", "azure_storage_logging_level")
    )
    logging.getLogger("transitions.core").setLevel(
        config.get("logging", "transitions_core_logging_level")
    )

    app = Flask(__name__)

    CORS(app, resources={r"/*": {"origins": config.get("network", "allowed_origins")}})

    app.config["RESTX_JSON"] = {"cls": EnhancedJSONEncoder}

    app.register_blueprint(api_blueprint)

    injector = Injector(
        [
            TelemetryModule,
            QueuesModule,
            StateMachineModule,
            StorageModule,
            SchedulerModule,
            ServiceModule,
            UtilitiesModule,
            RobotModule,
            ReaderModule,
            RequestHandlerModule,
            CoordinateModule,
        ]
    )

    FlaskInjector(
        app=app,
        injector=injector,
    )

    if not test_config:
        state_machine_thread = Thread(target=main, args=[injector])
        state_machine_thread.start()

    return app
