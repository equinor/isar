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
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.orientation import Orientation
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.mission import DriveToPose

api = Namespace(
    config.get("api_namespaces", "eqrobot_schedule_namespace"),
    description="Scheduling operations for the robot",
)

start_response = api.model(
    "mission_started", {"mission_started": fields.Boolean, "message": fields.String}
)


@api.route(
    "/drive-to",
    doc={
        "description": "Drives to specified position.",
        "params": {
            "x": {"description": "The target x coordinate", "type": "float"},
            "y": {"description": "The target y coordinate", "type": "float"},
            "z": {"description": "The target z coordinate", "type": "float"},
            "orientation": {
                "description": "The target orientation as a quaternion (x, y, z, w)",
                "type": "list",
            },
        },
    },
)
class DriveTo(Resource):
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
            x = float(request.args.get("x"))
            y = float(request.args.get("y"))
            z = float(request.args.get("z"))
            q: list = [
                float(item) for item in request.args.get("orientation").split(",")
            ]
        except Exception as e:
            message = asdict(
                StartMessage(
                    message="Could not read target pose parameters",
                    started=False,
                )
            )
            self.logger.error(f"{message} {e}")
            return message, HTTPStatus.BAD_REQUEST

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            return response

        position: Position = Position(x=x, y=y, z=z, frame=Frame.Robot)
        orientation: Orientation = Orientation(
            x=q[0], y=q[1], z=q[2], w=q[3], frame=Frame.Robot
        )
        pose: Pose = Pose(position=position, orientation=orientation, frame=Frame.Robot)

        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission([step])

        response = self.scheduling_utilities.start_mission(mission=mission)

        self.logger.info(response)
        return response
