import logging
from typing import Dict, List, Union

from azure.identity import DefaultAzureCredential
from injector import inject
from requests import Response
from requests.exceptions import RequestException

from isar.config.predefined_poses.predefined_poses import predefined_poses
from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.models.communication.messages import StartMissionMessages
from isar.models.mission import Mission
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.geometry.position import Position
from robot_interface.models.mission import DriveToPose, TakeImage, TakeThermalImage


class EchoPlanner(MissionPlannerInterface):
    @inject
    def __init__(
        self,
        request_handler: RequestHandler,
        stid_service: StidService,
    ):
        self.request_handler: RequestHandler = request_handler
        self.stid_service: StidService = stid_service
        self.credentials: DefaultAzureCredential = (
            AzureCredentials.get_azure_credentials()
        )
        self.logger = logging.getLogger("api")

    def get_mission(self, mission_id: int) -> Mission:
        """
        Retrieve robot mission from echo mission planner with specified id.
        :param mission_id: Unique id of echo mission plan
        :return: Mission object
        """
        mission_plan: dict = self._mission_plan(mission_id)

        try:
            plan_items: List[dict] = mission_plan["planItems"]
        except KeyError as e:
            msg: str = "Echo request body don't contain expected keys"
            self.logger.error(msg)
            raise MissionPlannerError(msg) from e

        mission: Mission = Mission(tasks=[])

        for plan_item in plan_items:
            try:
                tag_name: str = plan_item["tag"]
                sensors: List[str] = [
                    sensor_item["sensorTypeKey"]
                    for sensor_item in plan_item["sensorTypes"]
                ]
            except KeyError:
                self.logger.error("Echo request body don't contain expected keys")
                continue

            try:
                drive_task: DriveToPose = self._create_drive_task(tag_name=tag_name)
                inspection_tasks: List[
                    Union[TakeImage, TakeThermalImage]
                ] = self._create_inspection_tasks_from_sensor_types(
                    tag_name=tag_name, sensors=sensors
                )
            except (ValueError, RequestException) as e:
                self.logger.error(
                    f"Failed to create task with exception message: '{str(e)}'"
                )
                continue

            mission.tasks.append(drive_task)
            mission.tasks.extend(inspection_tasks)

        if not mission.tasks:
            raise MissionPlannerError(StartMissionMessages.empty_mission().message)

        mission.set_task_dependencies()
        return mission

    def _mission_plan(self, mission_id: int) -> dict:
        """
        Get mission plan from echo planner.
        :param mission_id: Unique id of echo mission plan
        """
        client_id: str = settings.ECHO_CLIENT_ID
        scope: str = settings.ECHO_APP_SCOPE
        request_scope: str = f"{client_id}/{scope}"

        token: str = self.credentials.get_token(request_scope).token

        url: str = f"{settings.ECHO_API_URL}/robots/robot-plan/{mission_id}"
        response: Response = self.request_handler.get(
            url=url,
            headers={"Authorization": f"Bearer {token}"},
        )

        return response.json()

    def _create_inspection_tasks_from_sensor_types(
        self, tag_name: str, sensors: List[str]
    ) -> List[Union[TakeImage, TakeThermalImage]]:
        tag_position: Position = self._get_tag_position(tag_name=tag_name)
        inspection_tasks: List[Union[TakeImage, TakeThermalImage]] = []
        for sensor in sensors:
            inspection: Union[
                TakeImage, TakeThermalImage
            ] = self._echo_sensor_type_to_isar_inspection_task(sensor_type=sensor)
            inspection.target = tag_position
            inspection.tag_id = tag_name
            inspection_tasks.append(inspection)
        return inspection_tasks

    def _get_robot_pose(self, tag_name: str) -> Pose:
        """
        Retrieve robot pose corresponding to inspection of a given tag. For now, this is a temporary hard-coded
        solution.
        """
        predefined_pose: Pose = predefined_poses[tag_name]

        if predefined_pose.frame is Frame.Robot:
            raise ValueError(
                f"Frame of predefined pose should be {Frame.Asset} not {Frame.Robot}"
            )

        return predefined_pose

    def _get_tag_position(self, tag_name: str) -> Position:
        tag_position: Position = self.stid_service.tag_position(tag_name)

        return tag_position

    def _create_drive_task(self, tag_name: str) -> DriveToPose:
        robot_pose: Pose = self._get_robot_pose(tag_name=tag_name)

        drive_task: DriveToPose = DriveToPose(pose=robot_pose)
        return drive_task

    @staticmethod
    def _echo_sensor_type_to_isar_inspection_task(
        sensor_type: str,
    ) -> Union[TakeImage, TakeThermalImage]:
        mapping: Dict[str, Union[TakeImage, TakeThermalImage]] = {
            "Picture": TakeImage(target=None),
            "ThermicPicture": TakeThermalImage(target=None),
        }
        return mapping[sensor_type]
