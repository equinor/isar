import logging
from http import HTTPStatus

from flask import Response
from flask_restx import Namespace, Resource, fields
from injector import inject

from models.geometry.joints import Joints
from models.geometry.pose import Pose
from robot_interfaces.robot_telemetry_interface import RobotTelemetryInterface

api = Namespace("telemetry", description="Retrieve robot telemetry")

position = api.model(
    "position",
    {
        "x": fields.Float(example="1.134"),
        "y": fields.Float(example="1.134"),
        "z": fields.Float(example="1.134"),
        "frame": fields.String(example="robot"),
    },
)

orientation = api.model(
    "q",
    {
        "q": fields.List(fields.Float, example=["0", "0", "0", "1"]),
        "frame": fields.String(example="robot"),
    },
)

pose = api.model(
    "pose",
    {
        "position": fields.Nested(position),
        "orientation": fields.Nested(orientation),
        "frame": fields.String(example="robot"),
    },
)

joints = api.model(
    "joints",
    {
        "j1": fields.Float(example="3.70002"),
        "j2": fields.Float(example="3.70002"),
        "j3": fields.Float(example="null"),
        "j4": fields.Float(example="null"),
        "j5": fields.Float(example="null"),
    },
)

success_pose = api.model(
    "current_pose", {"pose": fields.Nested(pose), "joints": fields.Nested(joints)}
)


@api.route(
    "/current-pose", doc={"description": "Retrieve the current pose of the robot"}
)
class CurrentPose(Resource):
    @inject
    def __init__(self, telemetry_service: RobotTelemetryInterface, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.telemetry_service = telemetry_service

    @api.response(HTTPStatus.OK, "Success", success_pose)
    @api.response(HTTPStatus.NOT_FOUND, "Not Found")
    def get(self):
        current_pose: Pose = self.telemetry_service.robot_pose()
        current_joints: Joints = self.telemetry_service.robot_joints()

        if current_pose is None or current_joints is None:
            return Response(
                "Could not retrieve current pose.", status=HTTPStatus.NOT_FOUND
            )

        pose_and_joints = {
            "pose": current_pose,
            "joints": current_joints,
        }
        return pose_and_joints
