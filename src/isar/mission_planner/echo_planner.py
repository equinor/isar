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
        mission: Mission = Mission(mission_steps=[])

        for tag in mission_tags:
            tag_name: str = tag["tag"]

            try:
                drive_step: DriveToPose = self._create_drive_step(tag_name=tag_name)
                measurement_steps: List[
                    Union[TakeImage, TakeThermalImage]
                ] = self._create_measurement_steps(tag_name=tag_name)
            except Exception as e:
                self.logger.error(e)
                continue

            mission.mission_steps.append(drive_step)
            for measurement_step in measurement_steps:
                mission.mission_steps.append(measurement_step)

        mission.mission_metadata.update_metadata(mission_plan)

        return mission

    def _mission_plan(self, mission_id: int) -> dict:
        """
        Get mission plan from echo planner.
        :param mission_id: Unique id of echo mission plan
        """
        token: str = self.credentials.get_token(
            config.get("echo", "echo_app_scope")
        ).token
        url: str = f"{config.get('echo', 'url')}/robots/robot-plan/{mission_id}"
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

    def _create_drive_step(self, tag_name: str) -> DriveToPose:
        robot_pose: Pose = self._get_robot_pose(tag_name=tag_name)

        drive_step: DriveToPose = DriveToPose(pose=robot_pose)
        return drive_step

    def _create_measurement_steps(
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

        measurement_steps: List[Union[TakeImage, TakeThermalImage]] = []
        for measurement_type in predefined_measurement_type:
            if measurement_type == "ThermalImage":
                measurement_steps.append(
                    self._create_thermal_image_step(tag_name=tag_name)
                )

            elif measurement_type == "Image":
                measurement_steps.append(self._create_image_step(tag_name=tag_name))

            else:
                self.logger.exception(
                    f"Invalid measurement type in predefined_measurement_types. Tag: {tag_name}, measurement type: {measurement_type}"
                )

        measurement_steps = [step for step in measurement_steps]

        return measurement_steps

    def _create_image_step(self, tag_name: str) -> TakeImage:
        tag_position_robot: Position = self._get_tag_position_robot(tag_name=tag_name)

        image_step: TakeImage = TakeImage(
            target=tag_position_robot,
            tag_id=tag_name,
        )
        return image_step

    def _create_thermal_image_step(self, tag_name: str) -> TakeThermalImage:
        tag_position_robot: Position = self._get_tag_position_robot(tag_name=tag_name)

        thermal_image_step: TakeThermalImage = TakeThermalImage(
            target=tag_position_robot,
            tag_id=tag_name,
        )

        return thermal_image_step
