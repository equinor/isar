import logging
from http import HTTPStatus

from fastapi import Body, HTTPException, Path
from opentelemetry import trace

from isar.apis.models.models import (
    ControlMissionResponse,
    StartMissionResponse,
    TaskResponse,
)
from isar.apis.models.start_mission_definition import (
    StartMissionDefinition,
    StopMissionDefinition,
    to_isar_mission,
)
from isar.config.settings import robot_settings, settings
from isar.mission_planner.mission_planner_interface import MissionPlannerError
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TASKS, InspectionTask, MoveArm

tracer = trace.get_tracer(__name__)


class SchedulingController:
    def __init__(
        self,
        scheduling_utilities: SchedulingUtilities,
    ):
        self.scheduling_utilities: SchedulingUtilities = scheduling_utilities
        self.logger = logging.getLogger("api")

    @tracer.start_as_current_span("start_mission_by_id")
    def start_mission_by_id(
        self,
        mission_id: str = Path(
            alias="id",
            title="Mission ID",
            description="ID-number for predefined mission",
        ),
    ) -> StartMissionResponse:
        self.logger.info("Received request to start mission with id %s", mission_id)

        state: States = self.scheduling_utilities.get_state()
        self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(state)

        mission: Mission = self.scheduling_utilities.get_mission(mission_id)

        self.scheduling_utilities.verify_robot_capable_of_mission(
            mission=mission, robot_capabilities=robot_settings.CAPABILITIES
        )

        self.logger.info("Starting mission with ISAR Mission ID: '%s'", mission.id)

        self.scheduling_utilities.start_mission(mission=mission)

        return self._api_response(mission)

    @tracer.start_as_current_span("start_mission")
    def start_mission(
        self,
        mission_definition: StartMissionDefinition = Body(
            default=None,
            embed=True,
            title="Mission Definition",
            description="Description of the mission in json format",
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

        state: States = self.scheduling_utilities.get_state()
        self.scheduling_utilities.verify_state_machine_ready_to_receive_mission(state)

        try:
            mission: Mission = to_isar_mission(
                start_mission_definition=mission_definition
            )
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

        self.logger.info("Starting mission: %s", mission.id)
        self.scheduling_utilities.start_mission(mission=mission)
        return self._api_response(mission)

    @tracer.start_as_current_span("return_home")
    def return_home(self) -> None:
        self.logger.info("Received request to return home")

        state: States = self.scheduling_utilities.get_state()
        self.scheduling_utilities.verify_state_machine_ready_to_receive_return_home_mission(
            state
        )

        self.scheduling_utilities.return_home()

    @tracer.start_as_current_span("pause_mission")
    def pause_mission(self) -> ControlMissionResponse:
        self.logger.info("Received request to pause current mission")

        state: States = self.scheduling_utilities.get_state()

        if state not in [
            States.Monitor,
            States.ReturningHome,
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

    @tracer.start_as_current_span("resume_mission")
    def resume_mission(self) -> ControlMissionResponse:
        self.logger.info("Received request to resume current mission")

        state: States = self.scheduling_utilities.get_state()

        if state not in [States.Paused, States.ReturnHomePaused]:
            error_message = (
                f"Conflict - Resume command received in invalid state - State: {state}"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

        resume_mission_response: ControlMissionResponse = (
            self.scheduling_utilities.resume_mission()
        )
        return resume_mission_response

    @tracer.start_as_current_span("stop_mission")
    def stop_mission(
        self,
        mission_id: StopMissionDefinition = Body(
            default=None,
            embed=True,
            title="Mission ID to stop",
            description="The mission ID of the mission being stopped, in json format",
        ),
    ) -> ControlMissionResponse:

        self.logger.info("Received request to stop current mission")

        state: States = self.scheduling_utilities.get_state()

        if (
            state == States.UnknownStatus
            or state == States.Stopping
            or state == States.BlockedProtectiveStop
            or state == States.Offline
            or state == States.Home
            or state == States.ReturningHome
        ):
            error_message = (
                f"Conflict - Stop command received in invalid state - State: {state}"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

        stop_mission_response: ControlMissionResponse = (
            self.scheduling_utilities.stop_mission(mission_id.mission_id)
        )
        return stop_mission_response

    @tracer.start_as_current_span("start_move_arm_mission")
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
        self.scheduling_utilities.start_mission(mission=mission)
        return self._api_response(mission)

    @tracer.start_as_current_span("release_intervention_needed")
    def release_intervention_needed(self) -> None:
        self.logger.info("Received request to release intervention needed state")

        state: States = self.scheduling_utilities.get_state()

        if state != States.InterventionNeeded:
            error_message = f"Conflict - Release intervention needed command received in invalid state - State: {state}"
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_message,
            )

        self.scheduling_utilities.release_intervention_needed()
        self.logger.info("Released intervention needed state successfully")

    @tracer.start_as_current_span("lockdown")
    def lockdown(self) -> None:
        self.logger.info("Received request to lockdown robot")

        state: States = self.scheduling_utilities.get_state()

        if state == States.Lockdown:
            error_message = "Conflict - Lockdown command received in lockdown state"
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_message,
            )

        self.scheduling_utilities.lock_down_robot()
        self.logger.info("Lockdown started successfully")

    @tracer.start_as_current_span("release_lockdown")
    def release_lockdown(self) -> None:
        self.logger.info("Received request to release robot lockdown")

        state: States = self.scheduling_utilities.get_state()

        if state != States.Lockdown:
            error_message = f"Conflict - Release lockdown command received in invalid state - State: {state}"
            self.logger.warning(error_message)
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=error_message,
            )

        self.scheduling_utilities.release_robot_lockdown()
        self.logger.info("Released lockdown successfully")

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
