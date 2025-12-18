import logging
from copy import deepcopy
from http import HTTPStatus
from typing import List, TypeVar

from fastapi import HTTPException

from isar.apis.models.models import ControlMissionResponse, MaintenanceResponse
from isar.config.settings import settings
from isar.models.events import (
    APIEvent,
    APIRequests,
    EventConflictError,
    Events,
    EventTimeoutError,
    SharedState,
)
from isar.services.service_connections.persistent_memory import (
    change_persistent_robot_state_is_maintenance_mode,
)
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission

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
        queue_timeout: int = settings.QUEUE_TIMEOUT,
    ):
        self.api_events: APIRequests = events.api_requests
        self.shared_state: SharedState = shared_state
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
            return home paused or returning home and therefore cannot start a new mission
        """
        if (
            state == States.Home
            or state == States.AwaitNextMission
            or state == States.ReturningHome
            or state == States.ReturnHomePaused
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
        if state == States.Home or state == States.AwaitNextMission:
            return True

        error_message = f"Conflict - Robot is not home, robot standing still or awaiting next mission - State: {state}"
        self.logger.warning(error_message)
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)

    def log_mission_overview(self, mission: Mission) -> None:
        """Log an overview of the tasks in a mission"""
        log_statements: List[str] = []
        for task in mission.tasks:
            log_statements.append(
                f"{type(task).__name__:<20} {str(task.id)[:8]:<32} -- {task.status}"
            )
        log_statement: str = "\n".join(log_statements)

        self.logger.info("Started mission:\n%s", log_statement)

    def start_mission(
        self,
        mission: Mission,
    ) -> None:
        """Start mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        HTTPException 409 Conflict
            If the state machine is not ready to receive a mission
        HTTPException 500 Internal Server Error
            If there is an unexpected error while sending the mission to the state machine
        """
        try:
            self.logger.info(
                "Requesting to start mission:\n"
                f"  Mission ID: {mission.id}\n"
                f"  Mission Name: {mission.name}\n"
                f"  Number of Tasks: {len(mission.tasks)}"
            )
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
        except Exception as e:
            error_message = "Unexpected error while sending mission to state machine"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        self.log_mission_overview(mission)
        self.logger.info("OK - Mission start successfully initiated")

    def return_home(
        self,
    ) -> None:
        """Start return home mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        HTTPException 409 Conflict
            If the state machine is not ready to receive a return home mission
        HTTPException 500 Internal Server Error
            If there is an unexpected error while sending the return home command
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
        except Exception as e:
            error_message = "Unexpected error while sending return home command"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        self.logger.info("OK - Return home mission start successfully initiated")

    def pause_mission(self) -> ControlMissionResponse:
        """Pause mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        HTTPException 409 Conflict
            If the state machine is not in a state which can pause a mission
        """
        try:
            response = self._send_command(True, self.api_events.pause_mission)
            if not response.success:
                self.logger.warning(
                    f"Mission failed to pause - {response.failure_reason}"
                )
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail=response.failure_reason,
                )
            self.logger.info("OK - Pause mission successfully initiated")
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
        except Exception as e:
            error_message = "Unexpected error while pausing mission"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def resume_mission(self) -> ControlMissionResponse:
        """Resume mission

        Raises
        ------
        HTTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        HTTPException 409 Conflict
            If the state machine is not in a state which can resume a mission
        HTTPException 500 Internal Server Error
            If there is an unexpected error while resuming the mission
        """
        try:
            response = self._send_command(True, self.api_events.resume_mission)
            self.logger.info("OK - Resume mission successfully initiated")
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
        except Exception as e:
            error_message = "Unexpected error while resuming mission"
            self.logger.error(f"{error_message}. Exception: {e}")
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
        HTTPException 409 Conflict
            If the state machine is not in a state which can stop a mission
        HTTPException 500 Internal Server Error
            If there is an unexpected error while stopping the mission
        """
        try:
            stop_mission_response: ControlMissionResponse = self._send_command(
                mission_id, self.api_events.stop_mission
            )

            if not stop_mission_response.success:
                error_message = (
                    f"Failed to stop mission: {stop_mission_response.failure_reason}"
                )
                self.logger.error(error_message)
                raise HTTPException(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=error_message
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
        except HTTPException as e:
            raise e
        except Exception as e:
            error_message = "Unexpected error while stopping mission"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )
        self.logger.info("OK - Stop mission successfully initiated")
        return stop_mission_response

    def release_intervention_needed(self) -> None:
        """Release intervention needed state

        Raises
        ------
        HTTPException 409 Conflict
            If the state machine is not in intervention needed state
        HTTPException 408 Request timeout
            If there is a timeout while communicating with the state machine
        HTTPException 500 Internal Server Error
            If the intervention needed state could not be released
        """
        try:
            self._send_command(True, self.api_events.release_intervention_needed)
            self.logger.info("OK - Intervention needed state released")
        except EventConflictError:
            error_message = (
                "Previous release intervention needed request is still being processed"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = "Cannot release intervention needed as it is not in intervention needed state"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except Exception as e:
            error_message = "Unexpected error while releasing intervention needed state"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def lock_down_robot(self) -> None:
        """Lock down robot

        Raises
        ------
        HTTPException 409 Conflict
            If the state machine is not in a state which can be locked down
        HTTPException 500 Internal Server Error
            If the robot could not be locked down
        """
        try:
            self._send_command(True, self.api_events.send_to_lockdown)
            self.logger.info("OK - Robot sent into lockdown")
        except EventConflictError:
            error_message = "Previous lockdown request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = "Cannot send robot to lockdown as it is already in lockdown"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except Exception as e:
            error_message = "Unexpected error while locking down robot"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def release_robot_lockdown(self) -> None:
        """Release robot from lockdown

        Raises
        ------
        HTTPException 409 Conflict
            If the state machine is not in lockdown
        HTTPException 500 Internal Server Error
            If the robot could not be released from lockdown
        """
        try:
            self._send_command(True, self.api_events.release_from_lockdown)
            self.logger.info("OK - Robot released form lockdown")
        except EventConflictError:
            error_message = (
                "Previous release robot from lockdown request is still being processed"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = (
                "Cannot release robot from lockdown as it is not in lockdown"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except Exception as e:
            error_message = "Unexpected error while releasing robot from lockdown"
            self.logger.error(f"{error_message}. Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def set_maintenance_mode(self) -> None:
        """Set maintenance mode"""
        try:
            if settings.PERSISTENT_STORAGE_CONNECTION_STRING != "":
                change_persistent_robot_state_is_maintenance_mode(
                    settings.PERSISTENT_STORAGE_CONNECTION_STRING,
                    settings.ISAR_ID,
                    value=True,
                )
            response: MaintenanceResponse = self._send_command(
                True, self.api_events.set_maintenance_mode
            )
            if response.failure_reason is not None:
                self.logger.warning(response.failure_reason)
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="Conflict attempting to set maintenance mode",
                )
            self.logger.info("OK - Robot sent into maintenance mode")
        except EventConflictError:
            error_message = "Previous maintenance request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = (
                "Cannot send robot to maintenance as it is already in maintenance"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except Exception as e:
            error_message = "Unexpected error while setting maintenance mode"
            self.logger.error(f"{error_message} Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def release_maintenance_mode(self) -> None:
        """Release robot from maintenance mode"""
        try:
            self._send_command(True, self.api_events.release_from_maintenance_mode)
            if settings.PERSISTENT_STORAGE_CONNECTION_STRING != "":
                change_persistent_robot_state_is_maintenance_mode(
                    settings.PERSISTENT_STORAGE_CONNECTION_STRING,
                    settings.ISAR_ID,
                    value=False,
                )
            self.logger.info("OK - Robot released form maintenance mode")
        except EventConflictError:
            error_message = "Previous release robot from maintenance request is still being processed"
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except EventTimeoutError:
            error_message = (
                "Cannot release robot from maintenance as it is not in maintenance"
            )
            self.logger.warning(error_message)
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=error_message)
        except Exception as e:
            error_message = "Unexpected error while releasing maintenance mode"
            self.logger.error(f"{error_message} Exception: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
            )

    def _send_command(self, input: T1, api_event: APIEvent[T1, T2]) -> T2:
        if not api_event.lock.acquire(blocking=False):
            raise EventConflictError("API event has already been sent")

        try:
            if api_event.request.has_event():
                self.logger.error(
                    "API request already had pending request before sending request"
                )

            if api_event.response.has_event():
                self.logger.error(
                    "API request already had response before sending request"
                )

            api_event.request.clear_event()
            api_event.response.clear_event()

            api_event.request.trigger_event(input, timeout=1)
            return api_event.response.consume_event(timeout=self.queue_timeout)
        except EventTimeoutError as e:
            self.logger.error("Queue timed out")
            api_event.request.clear_event()
            self.logger.error("No output received for command to state machine")
            raise e
        finally:
            api_event.request.clear_event()
            api_event.response.clear_event()
            api_event.lock.release()
