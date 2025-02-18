import logging
from http import HTTPStatus
from typing import Optional

from alitra import Pose
from fastapi import Body, HTTPException, Path
from injector import inject
from threading import Lock
from isar.apis.models.models import (
    ControlMissionResponse,
    TaskResponse,
    InputPose,
    StartMissionResponse,
)
from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    to_isar_mission,
)
from isar.config.settings import robot_settings, settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    TASKS,
    InspectionTask,
    MoveArm,
    ReturnToHome,
)


class SchedulingController:
    @inject
    def __init__(
        self,
        scheduling_utilities: SchedulingUtilities,
    ):
        self.scheduling_utilities: SchedulingUtilities = scheduling_utilities
        self.logger = logging.getLogger("api")
        self.start_mission_lock: Lock = Lock()

    def start_mission_by_id(
        self,
        mission_id: str = Path(
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
            mission.tasks.append(ReturnToHome(pose=pose))

        self.scheduling_utilities.verify_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )

        initial_pose_alitra: Optional[Pose] = (
            initial_pose.to_alitra_pose() if initial_pose else None
        )

        self.logger.info(f"Starting mission with ISAR Mission ID: '{mission.id}'")

        self.scheduling_utilities.start_mission(
            mission=mission, initial_pose=initial_pose_alitra
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
            error_message_no_mission_definition: str = (
                "Unprocessable entity - 'mission_definition' empty or invalid"
            )
            self.logger.error(error_message_no_mission_definition)
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=error_message_no_mission_definition,
            )

        if not self.start_mission_lock.acquire(blocking=False):
            error_message_another_mission_starting: str = (
                "Conflict - Another mission is currently being started"
            )
            self.logger.warning(error_message_another_mission_starting)
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_message_another_mission_starting,
            )

        try:
            state: States = self.scheduling_utilities.get_state()
            self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(
                state
            )

            try:
                mission: Mission = to_isar_mission(
                    start_mission_definition=mission_definition, return_pose=return_pose
                )
            except MissionPlannerError as e:
                error_message_mission_planner: str = (
                    f"Bad Request - Cannot create ISAR mission: {e}"
                )
                self.logger.warning(error_message_mission_planner)
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail=error_message_mission_planner,
                )

            self.scheduling_utilities.verify_robot_capable_of_mission(
                mission=mission, robot_capabilities=robot_settings.CAPABILITIES
            )

            initial_pose_alitra: Optional[Pose] = (
                initial_pose.to_alitra_pose() if initial_pose else None
            )

            self.logger.info(f"Starting mission: {mission.id}")
            self.scheduling_utilities.start_mission(
                mission=mission, initial_pose=initial_pose_alitra
            )
            return self._api_response(mission)

        finally:
            self.start_mission_lock.release()

    def pause_mission(self) -> ControlMissionResponse:
        self.logger.info("Received request to pause current mission")

        state: States = self.scheduling_utilities.get_state()

        if state not in [
            States.Monitor,
            States.Initiate,
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

        if state == States.Off:
            error_message = (
                f"Conflict - Stop command received in invalid state - State: {state}"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

        stop_mission_response: ControlMissionResponse = (
            self.scheduling_utilities.stop_mission()
        )
        return stop_mission_response

    def start_move_arm_mission(
        self,
        arm_pose_literal: str = Path(
            ...,
            alias="arm_pose_literal",
            title="Arm pose literal",
            description="Arm pose as a literal",
        ),
    ) -> StartMissionResponse:
        self.logger.info("Received request to start new move arm mission")

        if not robot_settings.VALID_ARM_POSES:
            error_message: str = (
                f"Received a request to move the arm but the robot "
                f"{settings.ROBOT_NAME} does not support moving an arm"
            )
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=error_message
            )

        if arm_pose_literal not in robot_settings.VALID_ARM_POSES:
            error_message = (
                f"Received a request to move the arm but the arm pose "
                f"{arm_pose_literal} is not supported by the robot "
                f"{settings.ROBOT_NAME}"
            )
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=error_message
            )

        state: States = self.scheduling_utilities.get_state()

        self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(state)

        mission: Mission = Mission(
            name="Move arm mission", tasks=[MoveArm(arm_pose=arm_pose_literal)]
        )

        self.logger.info(
            f"Starting move arm mission with ISAR Mission ID: '{mission.id}'"
        )
        self.scheduling_utilities.start_mission(
            mission=mission,
            initial_pose=None,
        )
        return self._api_response(mission)

    def _api_response(self, mission: Mission) -> StartMissionResponse:
        return StartMissionResponse(
            id=mission.id,
            tasks=[self._task_api_response(task) for task in mission.tasks],
        )

    def _task_api_response(self, task: TASKS) -> TaskResponse:
        if isinstance(task, InspectionTask):
            inspection_id = task.inspection_id
        else:
            inspection_id = None

        return TaskResponse(
            id=task.id, tag_id=task.tag_id, inspection_id=inspection_id, type=task.type
        )
