from flask import Blueprint
from flask_restx import Api

from isar.apis.missions.list_predefined_missions import api as predefined_missions_api
from isar.apis.schedule.drive_to import api as drive_to_api
from isar.apis.schedule.image_towards_coordinate import api as image_coordinate_api
from isar.apis.schedule.start_echo_mission import api as start_echo_mission_api
from isar.apis.schedule.start_mission import api as start_mission_api
from isar.apis.schedule.stop_mission import api as stop_mission_api
from isar.apis.telemetry.mission_status import api as mission_status_api
from isar.apis.telemetry.telemetry import api as telemetry_api

api_blueprint = Blueprint("api", __name__)

api = Api(
    api_blueprint,
    title="ISAR",
    version="0.1",
    description="Integration and Supervisory control of Autonomous Robots",
)

api.add_namespace(start_mission_api, path="/schedule")
api.add_namespace(start_echo_mission_api, path="/schedule")
api.add_namespace(stop_mission_api, path="/schedule")
api.add_namespace(drive_to_api, path="/schedule")
api.add_namespace(image_coordinate_api, path="/schedule")

api.add_namespace(predefined_missions_api, path="/missions")

api.add_namespace(telemetry_api, path="/telemetry")
api.add_namespace(mission_status_api, path="/telemetry")
