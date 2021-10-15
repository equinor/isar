import logging
from http import HTTPStatus

from flask_restx import Namespace, Resource
from injector import inject
from isar.config import config
from isar.mission_planner.local_planner import LocalPlanner

api = Namespace(
    config.get("api_namespaces", "eqrobot_missions_namespace"),
    description="CRUD operations for missions",
)


@api.route(
    "/list-predefined-missions",
    doc={"description": "Lists available predefined missions"},
)
class ListPredefinedMissions(Resource):
    @inject
    def __init__(self, mission_reader: LocalPlanner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("api")
        self.mission_reader = mission_reader

    @api.response(HTTPStatus.OK, "Success")
    @api.response(HTTPStatus.NOT_FOUND, "Not found")
    def get(self):
        try:
            predefined_missions = self.mission_reader.list_predefined_missions()
        except Exception:
            response = "Failed to reach predefined mission", HTTPStatus.NOT_FOUND
            self.logger.error(response)
            return response

        response = predefined_missions, HTTPStatus.OK
        self.logger.info(response)
        return response
