import logging
from typing import List, Union

from azure.identity import DefaultAzureCredential
from injector import inject
from requests import Response

from isar.config import config
from isar.config.predefined_measurement_types.predefined_measurement_types import (
    predefined_measurement_types,
)
from isar.config.predefined_poses.predefined_poses import predefined_poses
from isar.mission_planner.mission_planner_interface import MissionPlannerInterface
from isar.models.mission import Mission
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.coordinates.transformation import Transformation
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
        transform: Transformation,
    ):
        self.request_handler: RequestHandler = request_handler
        self.stid_service: StidService = stid_service
        self.transform: Transformation = transform
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

        mission_tags: List[dict] = mission_plan["planItems"]
        mission: Mission = Mission(tasks=[])

        for tag in mission_tags:
            tag_name: str = tag["tag"]

            try:
                drive_task: DriveToPose = self._create_drive_task(tag_name=tag_name)
                measurement_tasks: List[
                    Union[TakeImage, TakeThermalImage]
                ] = self._create_measurement_tasks(tag_name=tag_name)
            except Exception as e:
                self.logger.error(e)
                continue

            mission.tasks.append(drive_task)
            for measurement_task in measurement_tasks:
                mission.tasks.append(measurement_task)

        mission.metadata.update_metadata(mission_plan)
        mission.set_task_dependencies()

        return mission

    def _mission_plan(self, mission_id: int) -> dict:
        """
        Get mission plan from echo planner.
        :param mission_id: Unique id of echo mission plan
        """
        client_id: str = config.get("service_connections", "echo_client_id")
        scope: str = config.get("service_connections", "echo_app_scope")
        request_scope: str = f"{client_id}/{scope}"

        token: str = self.credentials.get_token(request_scope).token

        url: str = f"{config.get('service_connections', 'echo_api_url')}/robots/robot-plan/{mission_id}"
        response: Response = self.request_handler.get(
            url=url,
            headers={"Authorization": f"Bearer {token}"},
        )

        return response.json()

    def _get_robot_pose(self, tag_name: str) -> Pose:
        """
        Retrieve robot pose corresponding to inspection of a given tag. For now, this is a temporary hard-coded
        solution.
        """
        predefined_pose: Pose = predefined_poses[tag_name]

        if predefined_pose.frame is Frame.Robot:
            return predefined_pose

        predefined_pose = self.transform.transform_pose(
            predefined_pose, to_=Frame.Robot
        )

        return predefined_pose

    def _get_tag_position_robot(self, tag_name: str) -> Position:
        tag_position_asset: Position = self.stid_service.tag_position(tag_name)
        tag_position_robot: Position = self.transform.transform_position(
            tag_position_asset, to_=Frame.Robot
        )
        return tag_position_robot

    def _create_drive_task(self, tag_name: str) -> DriveToPose:
        robot_pose: Pose = self._get_robot_pose(tag_name=tag_name)

        drive_task: DriveToPose = DriveToPose(pose=robot_pose)
        return drive_task

    def _create_measurement_tasks(
        self, tag_name: str
    ) -> List[Union[TakeImage, TakeThermalImage]]:
        """
        Retrieve measurement type corresponding to inspection of a given tag. For now, this is a temporary hard-coded
        solution.
        """
        try:
            predefined_measurement_type: List[str] = predefined_measurement_types[
                tag_name
            ]
        except KeyError:
            self.logger.warning(
                f"Tag not in predefined_measurement_types, will use default. Tag: {tag_name}"
            )
            predefined_measurement_type = ["Image"]

        measurement_tasks: List[Union[TakeImage, TakeThermalImage]] = []
        for measurement_type in predefined_measurement_type:
            if measurement_type == "ThermalImage":
                measurement_tasks.append(
                    self._create_thermal_image_task(tag_name=tag_name)
                )

            elif measurement_type == "Image":
                measurement_tasks.append(self._create_image_task(tag_name=tag_name))

            else:
                self.logger.exception(
                    f"Invalid measurement type in predefined_measurement_types. Tag: {tag_name}, measurement type: {measurement_type}"
                )

        measurement_tasks = [task for task in measurement_tasks]

        return measurement_tasks

    def _create_image_task(self, tag_name: str) -> TakeImage:
        tag_position_robot: Position = self._get_tag_position_robot(tag_name=tag_name)

        image_task: TakeImage = TakeImage(
            target=tag_position_robot,
            tag_id=tag_name,
        )
        return image_task

    def _create_thermal_image_task(self, tag_name: str) -> TakeThermalImage:
        tag_position_robot: Position = self._get_tag_position_robot(tag_name=tag_name)

        thermal_image_task: TakeThermalImage = TakeThermalImage(
            target=tag_position_robot,
            tag_id=tag_name,
        )

        return thermal_image_task
