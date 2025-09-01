import logging
from copy import deepcopy
from http import HTTPStatus
from typing import List, TypeVar

from fastapi import HTTPException
from requests import HTTPError

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.mission_planner.mission_planner_interface import (
    MissionNotFoundError,
    MissionPlannerError,
    MissionPlannerInterface,
)
from isar.models.events import (
    APIEvent,
    APIRequests,
    EventConflictError,
    Events,
    EventTimeoutError,
    SharedState,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class SchedulingUtilities:
    """
    Contains utility functions for scheduling missions from the API. The class handles
    required thread communication through queues to the state machine.
    """

    def __init__(
        self,
        events: Events,
        shared_state: SharedState,
        mission_planner: MissionPlannerInterface,
        queue_timeout: int = settings.QUEUE_TIMEOUT,
    ):
        self.api_events: APIRequests = events.api_requests
        self.shared_state: SharedState = shared_state
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
        current_state = self.shared_state.state.check()
        if current_state is None:
            error_message: str = (
                "Internal Server Error - Current state of the state machine is unknown"
            )
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        return current_state

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
        missing_capabilities = {
            task.type for task in mission.tasks if task.type not in robot_capabilities
        }

        if missing_capabilities:
            error_message = (
                f"Bad Request - Robot is not capable of performing mission."
                f" Missing functionalities: {missing_capabilities}."
            )
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=error_message,
            )

        return True

    def verify_state_machine_ready_to_receive_mission(self, state: States) -> bool:
        """Verify that the state machine is ready to receive a mission

        Raises
        ------
        HTTPException 409 Conflict
            If state machine is not home, robot standing still, awaiting next mission
            or returning home and therefore cannot start a new mission
        """
        if (
            state == States.RobotStandingStill
            or state == States.Home
            or state == States.AwaitNextMission
            or state == States.ReturningHome
        ):
            return True

        error_message = f"Conflict - Robot is not home, robot standing still, awaiting next mission or returning home - State: {state}"
        self.logger.warning(error_message)
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

    def verify_state_machine_ready_to_receive_return_home_mission(
        self, state: States
    ) -> bool:
        """Verify that the state machine is ready to receive a return home mission

        Raises
        ------
        HTTPException 409 Conflict
            If state machine is not home, robot standing still or awaiting next mission
            and therefore cannot start a new return home mission
        """
        if (
            state == States.RobotStandingStill
            or state == States.Home
            or state == States.AwaitNextMission
        ):
            return True

        error_message = f"Conflict - Robot is not home, robot standing still or awaiting next mission - State: {state}"
        self.logger.warning(error_message)
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

    def start_mission(
        self,
        mission: Mission,
    ) -> None:
        """Start mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            mission_start_response = self._send_command(
                deepcopy(mission),
                self.api_events.start_mission,
            )
            if not mission_start_response.mission_started:
                self.logger.warning(
                    f"Mission failed to start - {mission_start_response.mission_not_started_reason}"
                )
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=mission_start_response.mission_not_started_reason,
                )
        except EventConflictError:
            error_message = "Previous mission request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = (
                "State machine has entered a state which cannot start a mission"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        self.logger.info("OK - Mission started in ISAR")

    def return_home(
        self,
    ) -> None:
        """Start return home mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            self._send_command(
                True,
                self.api_events.return_home,
            )
        except EventConflictError:
            error_message = "Previous return home request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = "State machine has entered a state which cannot start a return home mission"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        self.logger.info("OK - Return home mission started in ISAR")

    def pause_mission(self) -> ControlMissionResponse:
        """Pause mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            response = self._send_command(True, self.api_events.pause_mission)
            self.logger.info("OK - Mission successfully paused")
            return response
        except EventConflictError:
            error_message = "Previous pause mission request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = (
                "State machine has entered a state which cannot pause a mission"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

    def resume_mission(self) -> ControlMissionResponse:
        """Resume mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            response = self._send_command(True, self.api_events.resume_mission)
            self.logger.info("OK - Mission successfully resumed")
            return response
        except EventConflictError:
            error_message = "Previous resume mission request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = "Internal Server Error - Failed to resume mission"
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def stop_mission(self, mission_id: str = "") -> ControlMissionResponse:
        """Stop mission

        Raises
        ------
        HTTPException 404 Not Found
            If the mission_id was not known to Isar
        HTTPException 503 Service Unavailable
            The request was understood, but attempting to stop the mission failed
        HTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        """
        try:
            stop_mission_response: ControlMissionResponse = self._send_command(
                mission_id, self.api_events.stop_mission
            )

            if stop_mission_response.mission_not_found:
                error_message = f"Mission ID {stop_mission_response.mission_id} is not currently running"
                self.logger.error(error_message)
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail=error_message
                )

            if stop_mission_response.mission_status != MissionStatus.Cancelled.value:
                error_message = "Failed to stop mission"
                self.logger.error(error_message)
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT, detail=error_message
                )
        except EventConflictError:
            error_message = "Previous stop mission request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = (
                "State machine has entered a state which cannot stop a mission"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        self.logger.info("OK - Mission successfully stopped")
        return stop_mission_response

    def release_intervention_needed(self) -> None:
        """Release intervention needed state

        Raises
        ------
        HTTPException 500 Internal Server Error
            If the intervention needed state could not be released
        """
        try:
            self._send_command(True, self.api_events.release_intervention_needed)
            self.logger.info("OK - Intervention needed state released")
        except EventTimeoutError:
            error_message = (
                "Internal Server Error - Failed to release intervention needed state"
            )
            self.logger.error(error_message)
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def _send_command(self, input: T1, api_event: APIEvent[T1, T2]) -> T2:
        if api_event.request.has_event() or api_event.response.has_event():
            raise EventConflictError("API event has already been sent")

        try:
            api_event.request.trigger_event(input, timeout=1)
            return api_event.response.consume_event(timeout=self.queue_timeout)
        except EventTimeoutError as e:
            self.logger.error("Queue timed out")
            api_event.request.clear_event()
            self.logger.error("No output received for command to state machine")
            raise e
