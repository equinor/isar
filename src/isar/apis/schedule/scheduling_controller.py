import logging
from http import HTTPStatus
from typing import List, Optional

from alitra import Pose
from fastapi import Body, HTTPException, Path
from injector import inject

from isar.apis.models import InputPose, StartMissionResponse
from isar.apis.models.models import (
    ControlMissionResponse,
    RobotInfoResponse,
    TaskResponse,
)
from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    to_isar_mission,
)
from isar.config.settings import robot_settings, settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.step import DriveToPose
from robot_interface.models.mission.task import Task


class SchedulingController:
    @inject
    def __init__(
        self,
        scheduling_utilities: SchedulingUtilities,
    ):
        self.scheduling_utilities: SchedulingUtilities = scheduling_utilities
        self.logger = logging.getLogger("api")

    def start_mission_by_id(
        self,
        mission_id: str = Path(
            ...,
            alias="id",
            title="Mission ID",
            description="ID-number for predefined mission",
        ),
        initial_pose: Optional[InputPose] = Body(
            default=None,
            description="The starting point of the mission. Used for initial "
            "localization of robot",
            embed=True,
        ),
        return_pose: Optional[InputPose] = Body(
            default=None,
            description="End pose of the mission. The robot return to the specified "
            "pose after finishing all inspections",
            embed=True,
        ),
    ) -> StartMissionResponse:
        self.logger.info(f"Received request to start mission with id {mission_id}")

        state: States = self.scheduling_utilities.get_state()
        self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(state)

        mission: Mission = self.scheduling_utilities.get_mission(mission_id)
        if return_pose:
            pose: Pose = return_pose.to_alitra_pose()
            step: DriveToPose = DriveToPose(pose=pose)
            mission.tasks.append(Task(steps=[step]))

        self.scheduling_utilities.verify_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )

        initial_pose_alitra: Optional[Pose] = (
            initial_pose.to_alitra_pose() if initial_pose else None
        )

        self.logger.info(f"Starting mission with ISAR Mission ID: '{mission.id}'")
        metadata: MissionMetadata = MissionMetadata(mission.id)
        self.scheduling_utilities.start_mission(
            mission=mission, initial_pose=initial_pose_alitra, mission_metadata=metadata
        )
        return self._api_response(mission)

    def start_mission(
        self,
        mission_definition: StartMissionDefinition = Body(
            default=None,
            embed=True,
            title="Mission Definition",
            description="Description of the mission in json format",
        ),
        initial_pose: Optional[InputPose] = Body(
            default=None,
            description="The starting point of the mission. Used for initial "
            "localization of robot",
            embed=True,
        ),
        return_pose: Optional[InputPose] = Body(
            default=None,
            description="End pose of the mission. The robot return to the specified "
            "pose after finishing all inspections",
            embed=True,
        ),
    ) -> StartMissionResponse:
        self.logger.info("Received request to start new mission")

        if not mission_definition:
            error_message: str = (
                "Unprocessable entity - 'mission_definition' empty or invalid"
            )
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=error_message
            )

        state: States = self.scheduling_utilities.get_state()
        self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(state)

        try:
            mission: Mission = to_isar_mission(mission_definition)
        except MissionPlannerError as e:
            error_message = f"Bad Request - Cannot create ISAR mission: {e}"
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=error_message,
            )

        self.scheduling_utilities.verify_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )
        if return_pose:
            pose: Pose = return_pose.to_alitra_pose()
            step: DriveToPose = DriveToPose(pose=pose)
            mission.tasks.append(Task(steps=[step]))

        initial_pose_alitra: Optional[Pose] = (
            initial_pose.to_alitra_pose() if initial_pose else None
        )

        metadata: MissionMetadata = MissionMetadata(mission.id)
        self.logger.info(f"Starting mission: {mission.id}")
        self.scheduling_utilities.start_mission(
            mission=mission, mission_metadata=metadata, initial_pose=initial_pose_alitra
        )
        return self._api_response(mission)

    def pause_mission(self) -> ControlMissionResponse:
        self.logger.info("Received request to pause current mission")

        state: States = self.scheduling_utilities.get_state()

        if state not in [
            States.Monitor,
            States.InitiateStep,
        ]:
            error_message = (
                f"Conflict - Pause command received in invalid state - State: {state}"
            )
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_message,
            )

        pause_mission_response: ControlMissionResponse = (
            self.scheduling_utilities.pause_mission()
        )
        return pause_mission_response

    def resume_mission(self) -> ControlMissionResponse:
        self.logger.info("Received request to resume current mission")

        state: States = self.scheduling_utilities.get_state()

        if state != States.Paused:
            error_message = (
                f"Conflict - Resume command received in invalid state - State: {state}"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

        resume_mission_response: ControlMissionResponse = (
            self.scheduling_utilities.resume_mission()
        )
        return resume_mission_response

    def stop_mission(self) -> ControlMissionResponse:
        self.logger.info("Received request to stop current mission")

        state: States = self.scheduling_utilities.get_state()

        if state in [States.Off, States.Idle]:
            error_message = (
                f"Conflict - Stop command received in invalid state - State: {state}"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

        stop_mission_response: ControlMissionResponse = (
            self.scheduling_utilities.stop_mission()
        )
        return stop_mission_response

    def drive_to(
        self,
        target_pose: InputPose = Body(
            default=None,
            title="Target Pose",
            description="The target pose for the drive_to step",
        ),
    ) -> StartMissionResponse:
        self.logger.info("Received request to start new drive-to mission")

        state: States = self.scheduling_utilities.get_state()

        self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(state)

        pose: Pose = target_pose.to_alitra_pose()
        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission(tasks=[Task(steps=[step])])
        metadata: MissionMetadata = MissionMetadata(mission.id)
        self.logger.info(
            f"Starting drive to mission with ISAR Mission ID: '{mission.id}'"
        )
        self.scheduling_utilities.start_mission(
            mission=mission, initial_pose=None, mission_metadata=metadata
        )
        return self._api_response(mission)

    def get_info(self):
        return RobotInfoResponse(
            robot_package=settings.ROBOT_PACKAGE,
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            robot_map_name=settings.DEFAULT_MAP,
            robot_capabilities=robot_settings.CAPABILITIES,
            plant_short_name=settings.STID_PLANT_NAME,
        )

    def _api_response(self, mission: Mission) -> StartMissionResponse:
        return StartMissionResponse(
            id=mission.id,
            tasks=[self._task_api_response(task) for task in mission.tasks],
        )

    def _task_api_response(self, task: Task) -> TaskResponse:
        steps: List[dict] = []
        for step in task.steps:
            steps.append({"id": step.id, "type": step.__class__.__name__})

        return TaskResponse(id=task.id, tag_id=task.tag_id, steps=steps)
