import logging
from dataclasses import asdict
from http import HTTPStatus

from flask import request
from flask_restx import Namespace, Resource, fields
from injector import inject

from isar.config import config
from isar.models.communication.messages import StartMessage
from isar.models.mission import Mission
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from models.geometry.frame import Frame
from models.geometry.position import Position
from models.planning.step import TakeImage

api = Namespace(
    config.get("api_namespaces", "eqrobot_schedule_namespace"),
    description="Scheduling operations for the robot",
)
start_response = api.model(
    "mission_started", {"mission_started": fields.Boolean, "message": fields.String}
)


@api.route(
    "/take-image",
    doc={
        "description": f"Takes a image at the current robot location in direction of the specified coordinate in"
        + f" robot frame.",
        "params": {
            "x_target": {"description": f" Target coordinate x", "type": "float"},
            "y_target": {"description": f" Target coordinate y", "type": "float"},
        },
    },
)
class TakeImageOfObject(Resource):
    @inject
    def __init__(self, scheduling_utilities: SchedulingUtilities, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.scheduling_utilities = scheduling_utilities

    @api.response(HTTPStatus.OK, "Success", start_response)
    @api.response(HTTPStatus.REQUEST_TIMEOUT, "Request Timeout", start_response)
    @api.response(HTTPStatus.CONFLICT, "Conflict", start_response)
    @api.response(HTTPStatus.BAD_REQUEST, "Bad Request")
    @api.response(HTTPStatus.NOT_FOUND, "Not Found")
    def get(self):
        try:
            x_target = float(request.args.get("x_target"))
            y_target = float(request.args.get("y_target"))
            z_target = float(request.args.get("z_target"))
        except Exception as e:
            message = asdict(
                StartMessage(
                    message="Could not read target coordinates",
                    started=False,
                )
            )
            self.logger.error(f"{message} {e}")
            return message, HTTPStatus.BAD_REQUEST

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            return response

        step: TakeImage = TakeImage(
            target=Position(x=x_target, y=y_target, z=z_target, frame=Frame.Robot)
        )
        mission: Mission = Mission([step])
        response = self.scheduling_utilities.start_mission(mission=mission)

        self.logger.info(response)
        return response
