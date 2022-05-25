import logging
from typing import Dict, List, Optional, Union

from alitra import Frame, Pose, Position
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
from isar.models.mission import Mission, Task
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from robot_interface.models.mission import DriveToPose, TakeImage, TakeThermalImage
from robot_interface.models.mission.step import TakeThermalVideo, TakeVideo


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

        tasks: List[Task] = []

        for plan_item in plan_items:
            try:
                tag_id: str = plan_item["tag"]
                tag_position: Position = self._get_tag_position(tag_id=tag_id)
                drive_step: DriveToPose = self._create_drive_step(tag_id=tag_id)
                inspection_steps: List[
                    Union[TakeImage, TakeThermalImage, TakeVideo, TakeThermalVideo]
                ] = [
                    self._echo_sensor_to_isar_inspection_step(
                        sensor=sensor, tag_id=tag_id, tag_position=tag_position
                    )
                    for sensor in plan_item["sensorTypes"]
                ]
            except (ValueError, KeyError, RequestException) as e:
                self.logger.error(
                    f"Failed to create task with exception message: '{str(e)}'"
                )
                continue
            task: Task = Task(steps=[drive_step, *inspection_steps], tag_id=tag_id)
            tasks.append(task)

        if not tasks:
            raise MissionPlannerError("Empty mission")

        mission: Mission = Mission(tasks=tasks)

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

    def _get_robot_pose(self, tag_id: str) -> Pose:
        """
        Retrieve robot pose corresponding to inspection of a given tag. For now, this is
        a temporary hard-coded solution.
        """
        try:
            predefined_pose: Pose = predefined_poses[tag_id]
        except KeyError:
            raise KeyError(f"Tag not in list of predefined poses: {tag_id}")
        if predefined_pose.frame == Frame("robot"):
            raise ValueError("Frame of predefined pose should be asset not robot")

        return predefined_pose

    def _get_tag_position(self, tag_id: str) -> Position:
        tag_position: Position = self.stid_service.tag_position(tag_id)

        return tag_position

    def _create_drive_step(self, tag_id: str) -> DriveToPose:
        robot_pose: Pose = self._get_robot_pose(tag_id=tag_id)

        drive_step: DriveToPose = DriveToPose(pose=robot_pose)
        return drive_step

    @staticmethod
    def _echo_sensor_to_isar_inspection_step(
        sensor: dict, tag_id: str, tag_position: Position
    ) -> Union[TakeImage, TakeThermalImage, TakeVideo, TakeThermalVideo]:
        sensor_type: str = sensor["sensorTypeKey"]
        duration: Optional[float] = sensor["timeInSeconds"]
        inspection: Union[TakeImage, TakeThermalImage, TakeVideo, TakeThermalVideo]
        if sensor_type == "Picture":
            inspection = TakeImage(target=tag_position)
        elif sensor_type == "Video":
            inspection = TakeVideo(target=tag_position, duration=duration)
        elif sensor_type == "ThermicPicture":
            inspection = TakeThermalImage(target=tag_position)
        elif sensor_type == "ThermicVideo":
            inspection = TakeThermalVideo(target=tag_position, duration=duration)
        else:
            raise ValueError(f"No step supported for sensor_type {sensor_type}")
        inspection.tag_id = tag_id
        return inspection
