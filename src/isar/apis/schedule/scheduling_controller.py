import logging
from http import HTTPStatus
from queue import Empty
from typing import List, Optional

import numpy as np
from alitra import Frame, Orientation, Pose, Position
from fastapi import Body, Query, Response
from injector import inject
from requests import HTTPError

from isar.apis.models import ApiPose, StartMissionResponse
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

    def start_mission(
        self,
        response: Response,
        mission_id: int = Query(
            ...,
            alias="ID",
            title="Mission ID",
            description="ID-number for predefined mission",
        ),
        initial_pose: Optional[ApiPose] = Body(
            default=None,
            description="The starting point of the mission. Used for initial localization of robot",
            embed=True,
        ),
    ):
        self.logger.info("Received request to start new mission")
        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            self.logger.error(
                "Internal Server Error - Current state of state machine unknown"
            )
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        if state in [
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Monitor,
            States.Paused,
        ]:
            self.logger.warning("Conflict - Mission already in progress")
            response.status_code = HTTPStatus.CONFLICT.value
            return

        try:
            mission: Mission = self.mission_planner.get_mission(mission_id)
        except HTTPError as e:
            self.logger.error(e)
            response.status_code = e.response.status_code
            return
        except MissionPlannerError as e:
            self.logger.error(e)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        robot_capable: bool = is_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )
        if not robot_capable:
            self.logger.error(
                "Bad Request - Robot is not capable of performing mission"
            )
            response.status_code = HTTPStatus.BAD_REQUEST.value
            return

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

        try:
            self.scheduling_utilities.start_mission(
                mission=mission, initial_pose=initial_pose_alitra
            )
            self.logger.info("OK - Mission successfully started")
        except QueueTimeoutError:
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
            self.logger.error("Timeout - Failed to start mission")
            return
        return StartMissionResponse(**mission.api_response_dict())

    def pause_mission(self, response: Response):
        self.logger.info("Received request to pause current mission")

        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            self.logger.error(
                "Internal Server Error - Current state of state machine unknown"
            )
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        if state in [States.Idle, States.StopStep, States.Paused, States.Initialize]:
            self.logger.info("Conflict - Pause command received in invalid state")
            response.status_code = HTTPStatus.CONFLICT.value
            return

        try:
            self.scheduling_utilities.pause_mission()
            self.logger.info("OK - Mission successfully paused")
        except QueueTimeoutError:
            self.logger.error("Timeout - Failed to pause mission")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value

    def resume_mission(self, response: Response):
        self.logger.info("Received request to resume current mission")
        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            self.logger.error(
                "Internal Server Error - Current state of state machine unknown"
            )
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        if state in [
            States.Idle,
            States.InitiateStep,
            States.Monitor,
            States.StopStep,
            States.Initialize,
        ]:
            self.logger.info("Conflict - Resume command received in invalid state")
            response.status_code = HTTPStatus.CONFLICT.value
            return

        try:
            self.scheduling_utilities.resume_mission()
            self.logger.info("OK - Mission successfully resumed")
        except QueueTimeoutError:
            self.logger.error("Timeout - Failed to resume mission")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value

    def stop_mission(self, response: Response):
        self.logger.info("Received request to stop current mission")

        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            self.logger.error(
                "Internal Server Error - Current state of state machine unknown"
            )
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        if state in [States.Idle, States.Initialize]:
            self.logger.info("Conflict - Stop command received in invalid state")
            response.status_code = HTTPStatus.CONFLICT.value
            return

        try:
            self.scheduling_utilities.stop_mission()
            self.logger.info("OK - Mission successfully stopped")
        except QueueTimeoutError:
            self.logger.error("Timeout - Failed to stop mission")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value

    def drive_to(
        self,
        response: Response,
        x: float = Query(
            ...,
            alias="x-value",
            description="The target x coordinate",
        ),
        y: float = Query(
            ...,
            alias="y-value",
            description="The target y coordinate",
        ),
        z: float = Query(
            ...,
            alias="z-value",
            description="The target z coordinate",
        ),
        q: List[float] = Query(
            [0, 0, 0, 1],
            alias="quaternion",
            description="The target orientation as a quaternion (x,y,z,w)",
        ),
    ):
        try:
            state: States = self.scheduling_utilities.get_state()
        except Empty:
            self.logger.error(
                "Internal Server Error - Current state of state machine unknown"
            )
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
            return

        if state in [
            States.Initialize,
            States.InitiateStep,
            States.StopStep,
            States.Monitor,
            States.Paused,
        ]:
            self.logger.info("Conflict - Drivt to command received in invalid state")
            response.status_code = HTTPStatus.CONFLICT.value
            return

        robot_frame: Frame = Frame("robot")
        position: Position = Position(x=x, y=y, z=z, frame=robot_frame)
        orientation: Orientation = Orientation(
            x=q[0], y=q[1], z=q[2], w=q[3], frame=robot_frame
        )
        pose: Pose = Pose(position=position, orientation=orientation, frame=robot_frame)

        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission(tasks=[Task(steps=[step])])

        try:
            self.scheduling_utilities.start_mission(mission=mission, initial_pose=None)
            self.logger.info("OK - Drive to successfully started")
        except QueueTimeoutError:
            self.logger.error("Timout - Failed to start drive to")
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
