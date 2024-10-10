import logging
from copy import deepcopy
from http import HTTPStatus
from queue import Empty
from typing import Any, List, Optional, Set

from alitra import Pose
from fastapi import HTTPException
from injector import inject
from requests import HTTPError

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import (
    MissionNotFoundError,
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues import QueueIO, Queues, QueueTimeoutError
from isar.services.utilities.queue_utilities import QueueUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission


class SchedulingUtilities:
    """
    Contains utility functions for scheduling missions from the API. The class handles
    required thread communication through queues to the state machine.
    """

    @inject
    def __init__(
        self,
        queues: Queues,
        mission_planner: MissionPlannerInterface,
        queue_timeout: int = settings.QUEUE_TIMEOUT,
    ):
        self.queues: Queues = queues
        self.mission_planner: MissionPlannerInterface = mission_planner
        self.queue_timeout: int = queue_timeout
        self.logger = logging.getLogger("api")

    def get_state(self) -> States:
        """Return the current state of the state machine

        Raises
        ------
        HTTPException 500 Internal Server Error
            If the current state is not available on the queue
        """
        try:
            return self.queues.state.check()
        except Empty:
            error_message: str = (
                "Internal Server Error - Current state of the state machine is unknown"
            )
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def get_mission(self, mission_id: str) -> Mission:
        """Get the mission with mission_id from the current mission planner

        Raises
        ------
        HTTPException 404 Not Found
            If requested mission with mission_id is not found
        HTTPException 500 Internal Server Error
            If for some reason the mission can not be returned
        """
        try:
            return self.mission_planner.get_mission(mission_id)
        except HTTPError as e:
            self.logger.error(e)
            raise HTTPException(status_code=e.response.status_code)
        except MissionNotFoundError as e:
            self.logger.error(e)
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Mission with id '{mission_id}' not found",
            )
        except MissionPlannerError as e:
            self.logger.error(e)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Could not plan mission",
            )

    def verify_robot_capable_of_mission(
        self, mission: Mission, robot_capabilities: List[str]
    ) -> bool:
        """Verify that the robot is capable of performing this mission

        Raises
        ------
        HTTPException 400 Bad request
            If the robot is not capable of performing mission
        """
        is_capable: bool = True
        missing_capabilities: Set[str] = set()
        for task in mission.tasks:
            if not task.type in robot_capabilities:
                is_capable = False
                missing_capabilities.add(task.type)

        if not is_capable:
            error_message = (
                f"Bad Request - Robot is not capable of performing mission."
                f" Missing functionalities: {missing_capabilities}."
            )
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=error_message,
            )

        return is_capable

    def verify_state_machine_ready_to_receive_mission(self, state: States) -> bool:
        """Verify that the state machine is idle and ready to receive a mission

        Raises
        ------
        HTTPException 409 Conflict
            If state machine is not idle and therefore can not start a new mission
        """
        is_state_machine_ready_to_receive_mission = state == States.Idle
        if not is_state_machine_ready_to_receive_mission:
            error_message = f"Conflict - Mission already in progress - State: {state}"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

        return is_state_machine_ready_to_receive_mission

    def start_mission(
        self,
        mission: Mission,
        initial_pose: Optional[Pose],
    ) -> None:
        """Start mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            self._send_command(
                StartMissionMessage(
                    mission=deepcopy(mission),
                    initial_pose=initial_pose,
                ),
                self.queues.start_mission,
            )
        except QueueTimeoutError:
            error_message = "Internal Server Error - Failed to start mission in ISAR"
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        self.logger.info("OK - Mission started in ISAR")

    def pause_mission(self) -> ControlMissionResponse:
        """Pause mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            return self._send_command(True, self.queues.pause_mission)
        except QueueTimeoutError:
            error_message = "Internal Server Error - Failed to pause mission"
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        finally:
            self.logger.info("OK - Mission successfully paused")

    def resume_mission(self) -> ControlMissionResponse:
        """Resume mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            return self._send_command(True, self.queues.resume_mission)
        except QueueTimeoutError:
            error_message = "Internal Server Error - Failed to resume mission"
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        finally:
            self.logger.info("OK - Mission successfully resumed")

    def stop_mission(self) -> ControlMissionResponse:
        """Stop mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            stop_mission_response: ControlMissionResponse = self._send_command(
                True, self.queues.stop_mission
            )
        except QueueTimeoutError:
            error_message = "Internal Server Error - Failed to stop mission"
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        self.logger.info("OK - Mission successfully stopped")
        return stop_mission_response

    def _send_command(self, input: Any, queueio: QueueIO) -> Any:
        queueio.input.put(input)
        try:
            return QueueUtilities.check_queue(
                queueio.output,
                self.queue_timeout,
            )
        except QueueTimeoutError as e:
            QueueUtilities.clear_queue(queueio.input)
            self.logger.error("No output received for command to state machine")
            raise e
