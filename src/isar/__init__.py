import logging
import logging.config

import yaml
from flask import Flask
from flask_cors import CORS
from flask_injector import FlaskInjector
from injector import Injector

from isar.apis import api_blueprint
from isar.config import config
from isar.services.utilities.json_service import EnhancedJSONEncoder


def create_app(injector: Injector):
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

    FlaskInjector(
        app=app,
        injector=injector,
    )

    return app
