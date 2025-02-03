import logging
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, Optional, Tuple

from injector import inject
from transitions import State

from isar.config.settings import settings
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

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="monitor", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine

        self.logger = logging.getLogger("state_machine")

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        self.state_machine.mission_ongoing = False
        return

    def _run(self) -> None:
        awaiting_task_status: bool = False
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            if self.state_machine.should_pause_mission():
                transition = self.state_machine.pause  # type: ignore
                break

            if not self.state_machine.mission_ongoing:
                if self.state_machine.get_mission_started_event():
                    self.state_machine.mission_ongoing = True
                else:
                    time.sleep(settings.FSM_SLEEP_TIME)
                    continue

            mission_failed = self.state_machine.get_mission_failed_event()
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

                transition = self.state_machine.mission_failed_to_start  # type: ignore
                break

            status: TaskStatus

            task_failure: Optional[ErrorMessage] = (
                self.state_machine.get_task_failure_event()
            )
            if task_failure is not None:
                self.state_machine.current_task.error_message = task_failure
                self.logger.error(
                    f"Monitoring task {self.state_machine.current_task.id[:8]} failed "
                    f"because: {task_failure.error_description}"
                )
                status = TaskStatus.Failed
            else:
                status = self.state_machine.get_task_status_event()

            if status is None:
                if not awaiting_task_status:
                    self.state_machine.request_task_status(
                        self.state_machine.current_task
                    )
                    awaiting_task_status = True
                continue
            else:
                awaiting_task_status = False

            if not isinstance(status, TaskStatus):
                self.logger.error(
                    f"Received an invalid status update {status} when monitoring mission. "
                    "Only TaskStatus is expected."
                )
                break

            if self.state_machine.current_task is None:
                self.state_machine.iterate_current_task()

            self.state_machine.current_task.status = status

            if (
                not settings.UPLOAD_INSPECTIONS_ASYNC
                and self._should_upload_inspections()
            ):
                get_inspection_thread = ThreadedRequest(
                    self._queue_inspections_for_upload
                )
                get_inspection_thread.start_thread(
                    deepcopy(self.state_machine.current_mission),
                    deepcopy(self.state_machine.current_task),
                    name="State Machine Get Inspections",
                )

            if self.state_machine.current_task.is_finished():
                self._report_task_status(self.state_machine.current_task)
                self.state_machine.publish_task_status(
                    task=self.state_machine.current_task
                )

                self.state_machine.iterate_current_task()
                if self.state_machine.current_task is None:
                    transition = self.state_machine.mission_finished  # type: ignore
                    break

                # Report and update next task
                self.state_machine.current_task.update_task_status()
                self.state_machine.publish_task_status(
                    task=self.state_machine.current_task
                )

        transition()

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

        if not inspection:
            self.logger.warning(
                f"No inspection result data retrieved for task {str(current_task.id)[:8]}"
            )

        inspection.metadata.tag_id = current_task.tag_id

        message: Tuple[Inspection, Mission] = (
            inspection,
            mission,
        )
        self.state_machine.queues.upload_queue.put(message)
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
