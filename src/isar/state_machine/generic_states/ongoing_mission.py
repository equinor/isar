import logging
import time
from copy import deepcopy
from enum import Enum
from queue import Queue
from threading import Event
from typing import TYPE_CHECKING, Optional, Tuple

from isar.config.settings import settings
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_for_event_without_consumption,
    trigger_event,
)
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotRetrieveInspectionException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import InspectionTask, Task


class OngoingMissionStates(str, Enum):
    Monitor = "monitor"
    ReturningHome = "returningHome"


if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class OngoingMission:
    def __init__(
        self,
        state_machine: "StateMachine",
        state: OngoingMissionStates,
    ) -> None:
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.events = state_machine.events
        self.awaiting_task_status: bool = False
        self.signal_state_machine_to_stop: Event = (
            state_machine.signal_state_machine_to_stop
        )
        self.state: OngoingMissionStates = state

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        self.state_machine.mission_ongoing = False

    def _check_and_handle_stop_mission_event(self, event: Queue) -> bool:
        if check_for_event(event):
            self.state_machine.stop()  # type: ignore
            return True
        return False

    def _check_and_handle_pause_mission_event(self, event: Queue) -> bool:
        if check_for_event(event):
            self.state_machine.pause()  # type: ignore
            return True
        return False

    def _check_and_handle_mission_started_event(self, event: Queue) -> bool:
        if check_for_event(event):
            self.state_machine.mission_ongoing = True
            return True
        return False

    def _check_and_handle_mission_failed_event(self, event: Queue) -> bool:
        mission_failed: Optional[ErrorMessage] = check_for_event(event)
        if mission_failed is not None:
            self.state_machine.logger.warning(
                f"Failed to initiate mission "
                f"{str(self.state_machine.current_mission.id)[:8]} because: "
                f"{mission_failed.error_description}"
            )
            self.state_machine.current_mission.error_message = ErrorMessage(
                error_reason=mission_failed.error_reason,
                error_description=mission_failed.error_description,
            )
            self.state_machine.mission_failed_to_start()  # type: ignore
            return True
        return False

    def _check_and_handle_task_status_failed_event(self, event: Queue) -> bool:
        if not self.state_machine.mission_ongoing:
            return False

        task_failure: Optional[ErrorMessage] = check_for_event(event)
        if task_failure is not None:
            self.awaiting_task_status = False
            self.state_machine.current_task.error_message = task_failure
            self.logger.error(
                f"Monitoring task {self.state_machine.current_task.id[:8]} failed "
                f"because: {task_failure.error_description}"
            )
            return self._handle_new_task_status(TaskStatus.Failed)
        elif not self.awaiting_task_status:
            trigger_event(
                self.events.state_machine_events.task_status_request,
                self.state_machine.current_task.id,
            )
            self.awaiting_task_status = True
        return False

    def _check_and_handle_task_status_event(self, event: Queue) -> bool:
        if not self.state_machine.mission_ongoing:
            return False

        status: Optional[TaskStatus] = check_for_event(event)
        if status is not None:
            self.awaiting_task_status = False
            return self._handle_new_task_status(status)
        elif not self.awaiting_task_status:
            trigger_event(
                self.events.state_machine_events.task_status_request,
                self.state_machine.current_task.id,
            )
            self.awaiting_task_status = True
        return False

    def _handle_new_task_status(self, status: TaskStatus) -> bool:
        if self.state_machine.current_task is None:
            self.state_machine.iterate_current_task()

        self.state_machine.current_task.status = status

        if self.state_machine.current_task.is_finished():
            self._report_task_status(self.state_machine.current_task)
            self.state_machine.publish_task_status(task=self.state_machine.current_task)

            if self.state == OngoingMissionStates.ReturningHome:
                if status != TaskStatus.Successful:
                    self.state_machine.return_home_failed()  # type: ignore
                    return True
                self.state_machine.returned_home()  # type: ignore
                return True

            if self._should_upload_inspections():
                get_inspection_thread = ThreadedRequest(
                    self._queue_inspections_for_upload
                )
                get_inspection_thread.start_thread(
                    deepcopy(self.state_machine.current_mission),
                    deepcopy(self.state_machine.current_task),
                    name="State Machine Get Inspections",
                )

            self.state_machine.iterate_current_task()
            if self.state_machine.current_task is None:
                self.state_machine.mission_finished()  # type: ignore
                return True

            # Report and update next task
            self.state_machine.current_task.update_task_status()
            self.state_machine.publish_task_status(task=self.state_machine.current_task)
        return False

    def _check_and_handle_start_mission_event(
        self, event: Queue[StartMissionMessage]
    ) -> bool:
        if check_for_event_without_consumption(event):
            self.state_machine.stop()  # type: ignore
            return True

        return False

    def _run(self) -> None:
        self.awaiting_task_status = False
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.state.name
                )
                break

            if self._check_and_handle_stop_mission_event(
                self.events.api_requests.stop_mission.input
            ):
                break

            if (
                self.state == OngoingMissionStates.Monitor
                and self._check_and_handle_pause_mission_event(
                    self.events.api_requests.pause_mission.input
                )
            ):
                break

            self._check_and_handle_mission_started_event(
                self.events.robot_service_events.mission_started
            )

            if self._check_and_handle_mission_failed_event(
                self.events.robot_service_events.mission_failed
            ):
                break

            if (
                self.state == OngoingMissionStates.ReturningHome
                and self._check_and_handle_start_mission_event(
                    self.events.api_requests.start_mission.input
                )
            ):
                break

            if self._check_and_handle_task_status_failed_event(
                self.events.robot_service_events.task_status_failed
            ):
                break

            if self._check_and_handle_task_status_event(
                self.events.robot_service_events.task_status_updated
            ):
                break

            time.sleep(settings.FSM_SLEEP_TIME)

    def _queue_inspections_for_upload(
        self, mission: Mission, current_task: InspectionTask
    ) -> None:
        try:
            inspection: Inspection = self.state_machine.robot.get_inspection(
                task=current_task
            )
            if current_task.inspection_id != inspection.id:
                self.logger.warning(
                    f"The inspection_id of task ({current_task.inspection_id}) "
                    f"and result ({inspection.id}) is not matching. "
                    f"This may lead to confusions when accessing the inspection later"
                )

        except (RobotRetrieveInspectionException, RobotException) as e:
            self._set_error_message(e)
            self.logger.error(
                f"Failed to retrieve inspections because: {e.error_description}"
            )
            return

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve inspections because of unexpected error: {e}"
            )
            return

        if not inspection:
            self.logger.warning(
                f"No inspection result data retrieved for task {str(current_task.id)[:8]}"
            )

        inspection.metadata.tag_id = current_task.tag_id

        message: Tuple[Inspection, Mission] = (
            inspection,
            mission,
        )
        self.state_machine.events.upload_queue.put(message)
        self.logger.info(
            f"Inspection result: {str(inspection.id)[:8]} queued for upload"
        )

    def _report_task_status(self, task: Task) -> None:
        if task.status == TaskStatus.Failed:
            self.logger.warning(
                f"Task: {str(task.id)[:8]} was reported as failed by the robot"
            )
        elif task.status == TaskStatus.Successful:
            self.logger.info(
                f"{type(task).__name__} task: {str(task.id)[:8]} completed"
            )

    def _should_upload_inspections(self) -> bool:
        if settings.UPLOAD_INSPECTIONS_ASYNC:
            return False

        return (
            self.state_machine.current_task.is_finished()
            and self.state_machine.current_task.status == TaskStatus.Successful
            and isinstance(self.state_machine.current_task, InspectionTask)
        )

    def _set_error_message(self, e: RobotException) -> None:
        error_message: ErrorMessage = ErrorMessage(
            error_reason=e.error_reason, error_description=e.error_description
        )
        self.state_machine.current_task.error_message = error_message
