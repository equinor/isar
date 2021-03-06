import logging
from http import HTTPStatus
from queue import Empty
from typing import List, Optional

import numpy as np
from alitra import Frame, Orientation, Pose, Position
from fastapi import Body, Path, Response
from injector import inject
from requests import HTTPError

from isar.apis.models import InputPose, StartMissionResponse
from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    to_isar_mission,
)
from isar.config.settings import robot_settings, settings
from isar.mission_planner.mission_planner_interface import (
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.mission_planner.mission_validator import is_robot_capable_of_mission
from isar.models.communication.queues import QueueTimeoutError
from isar.models.mission import Mission, Task
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission import DriveToPose


class SchedulingController:
    @inject
    def __init__(
        self,
        mission_planner: MissionPlannerInterface,
        scheduling_utilities: SchedulingUtilities,
        queue_timeout: int = settings.QUEUE_TIMEOUT,
    ):
        self.logger = logging.getLogger("api")
        self.mission_planner: MissionPlannerInterface = mission_planner
        self.scheduling_utilities: SchedulingUtilities = scheduling_utilities
        self.queue_timeout: int = queue_timeout

    def start_mission_by_id(
        self,
        response: Response,
        mission_id: int = Path(
            ...,
            alias="id",
            title="Mission ID",
            description="ID-number for predefined mission",
        ),
        initial_pose: Optional[InputPose] = Body(
            default=None,
            description="The starting point of the mission. Used for initial localization of robot",
            embed=True,
        ),
        return_pose: Optional[InputPose] = Body(
            default=None,
            description="End pose of the mission. The robot return to the specified pose after finsihing all inspections",
            embed=True,
        ),
    ):
        self.logger.info(f"Received request to start mission with id {mission_id}")
        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            errorMsg: str = (
                "Internal Server Error - Current state of state machine unknown"
            )
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return errorMsg

        if state in [
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Monitor,
            States.Paused,
        ]:
            errorMsg = "Conflict - Mission already in progress"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.CONFLICT.value
            return errorMsg

        try:
            mission: Mission = self.mission_planner.get_mission(mission_id)
        except HTTPError as e:
            self.logger.error(e)
            response.status_code = e.response.status_code
            raise
        except MissionPlannerError as e:
            self.logger.error(e)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        robot_capable: bool
        missing_functions: List[str]
        (robot_capable, missing_functions) = is_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )
        if not robot_capable:
            errorMsg = (
                "Bad Request - Robot is not capable of performing mission. Missing functionalities: "
                + str(missing_functions)
            )
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return errorMsg

        initial_pose_alitra: Optional[Pose]
        if initial_pose:
            initial_pose_alitra = Pose(
                position=Position(
                    x=initial_pose.x,
                    y=initial_pose.y,
                    z=initial_pose.z,
                    frame=Frame("asset"),
                ),
                orientation=Orientation.from_euler_array(
                    euler=np.array(
                        [initial_pose.roll, initial_pose.pitch, initial_pose.yaw]
                    ),
                    frame=Frame("asset"),
                ),
                frame=Frame("asset"),
            )
        else:
            initial_pose_alitra = None

        self.logger.info(f"Starting mission: {mission.id}")

        if return_pose:
            pose: Pose = Pose(
                position=Position(
                    x=return_pose.x,
                    y=return_pose.y,
                    z=return_pose.z,
                    frame=Frame("asset"),
                ),
                orientation=Orientation.from_euler_array(
                    np.array([return_pose.roll, return_pose.pitch, return_pose.yaw]),
                    Frame("asset"),
                ),
                frame=Frame("asset"),
            )
            step: DriveToPose = DriveToPose(pose=pose)
            mission.tasks.append(Task(steps=[step]))
        try:
            self.scheduling_utilities.start_mission(
                mission=mission, initial_pose=initial_pose_alitra
            )
            self.logger.info("OK - Mission successfully started")
        except QueueTimeoutError:
            errorMsg = "Timeout - Failed to start mission"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return errorMsg
        return StartMissionResponse(**mission.api_response_dict())

    def start_mission(
        self,
        response: Response,
        mission_definition: StartMissionDefinition = Body(
            default=None,
            embed=True,
            title="Mission Definition",
            description="Description of the mission in json format",
        ),
        initial_pose: Optional[InputPose] = Body(
            default=None,
            description="The starting point of the mission. Used for initial localization of robot",
            embed=True,
        ),
        return_pose: Optional[InputPose] = Body(
            default=None,
            description="End pose of the mission. The robot return to the specified pose after finsihing all inspections",
            embed=True,
        ),
    ):
        self.logger.info("Received request to start new mission")

        if not mission_definition:
            errorMsg: str = (
                "Unprocessable entity - 'mission_definition' empty or invalid"
            )
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.UNPROCESSABLE_ENTITY.value
            return errorMsg

        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            errorMsg = "Internal Server Error - Current state of state machine unknown"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return errorMsg

        if state in [
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Monitor,
            States.Paused,
        ]:
            errorMsg = "Conflict - Mission already in progress"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.CONFLICT.value
            return errorMsg

        try:
            mission: Mission = to_isar_mission(mission_definition)
        except MissionPlannerError as e:
            errorMsg = f"Bad Request - Cannot create ISAR mission: {e}"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return errorMsg

        robot_capable: bool
        missing_functions: List[str]
        (robot_capable, missing_functions) = is_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )
        if not robot_capable:
            errorMsg = (
                "Bad Request - Robot is not capable of performing mission. Missing functionalities: "
                + str(missing_functions)
            )
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return errorMsg

        initial_pose_alitra: Optional[Pose]
        if initial_pose:
            initial_pose_alitra = initial_pose.to_alitra_pose()
        else:
            initial_pose_alitra = None

        self.logger.info(f"Starting mission: {mission.id}")

        if return_pose:
            pose: Pose = return_pose.to_alitra_pose()
            step: DriveToPose = DriveToPose(pose=pose)
            mission.tasks.append(Task(steps=[step]))
        try:
            self.scheduling_utilities.start_mission(
                mission=mission, initial_pose=initial_pose_alitra
            )
            self.logger.info("OK - Mission successfully started")
        except QueueTimeoutError:
            errorMsg = "Timeout - Failed to start mission"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return errorMsg
        return StartMissionResponse(**mission.api_response_dict())

    def pause_mission(self, response: Response):
        self.logger.info("Received request to pause current mission")

        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            errorMsg = "Internal Server Error - Current state of state machine unknown"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return errorMsg

        if state in [States.Idle, States.StopStep, States.Paused, States.Initialize]:
            errorMsg = "Conflict - Pause command received in invalid state"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.CONFLICT.value
            return errorMsg

        try:
            self.scheduling_utilities.pause_mission()
            self.logger.info("OK - Mission successfully paused")
        except QueueTimeoutError:
            errorMsg = "Timeout - Failed to pause mission"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return errorMsg

    def resume_mission(self, response: Response):
        self.logger.info("Received request to resume current mission")
        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            errorMsg = "Internal Server Error - Current state of state machine unknown"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return errorMsg

        if state in [
            States.Idle,
            States.InitiateStep,
            States.Monitor,
            States.StopStep,
            States.Initialize,
        ]:
            errorMsg = "Conflict - Resume command received in invalid state"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.CONFLICT.value
            return errorMsg

        try:
            self.scheduling_utilities.resume_mission()
            self.logger.info("OK - Mission successfully resumed")
        except QueueTimeoutError:
            errorMsg = "Timeout - Failed to resume mission"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return errorMsg

    def stop_mission(self, response: Response):
        self.logger.info("Received request to stop current mission")

        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            errorMsg = "Internal Server Error - Current state of state machine unknown"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return errorMsg

        if state in [States.Idle, States.Initialize]:
            errorMsg = "Conflict - Stop command received in invalid state"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.CONFLICT.value
            return errorMsg

        try:
            self.scheduling_utilities.stop_mission()
            self.logger.info("OK - Mission successfully stopped")
        except QueueTimeoutError:
            errorMsg = "Timeout - Failed to stop mission"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return errorMsg

    def drive_to(
        self,
        response: Response,
        target_pose: InputPose = Body(
            default=None,
            title="Target Pose",
            description="The target pose for the drive_to step",
        ),
    ):
        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            errorMsg = "Internal Server Error - Current state of state machine unknown"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return errorMsg

        if state in [
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Monitor,
            States.Paused,
        ]:
            errorMsg = "Conflict - DriveTo command received in invalid state"
            self.logger.warning(errorMsg)
            response.status_code = HTTPStatus.CONFLICT.value
            return errorMsg

        pose: Pose = target_pose.to_alitra_pose()

        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission(tasks=[Task(steps=[step])])

        try:
            self.scheduling_utilities.start_mission(mission=mission, initial_pose=None)
            self.logger.info("OK - Drive to successfully started")
        except QueueTimeoutError:
            errorMsg = "Timeout - Failed to start DriveTo"
            self.logger.error(errorMsg)
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            return errorMsg
