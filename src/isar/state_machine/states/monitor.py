import logging
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, Optional, Sequence, Tuple, Union

from injector import inject
from transitions import State

from isar.config.settings import settings
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotRetrieveInspectionException,
    RobotTaskStatusException,
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
        self.request_status_failure_counter: int = 0
        self.request_status_failure_counter_limit: int = (
            settings.REQUEST_STATUS_FAILURE_COUNTER_LIMIT
        )

        self.logger = logging.getLogger("state_machine")
        self.task_status_thread: Optional[ThreadedRequest] = None

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.task_status_thread:
            self.task_status_thread.wait_for_thread()
        self.task_status_thread = None

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            if self.state_machine.should_pause_mission():
                if self.state_machine.run_mission_by_task:
                    transition = self.state_machine.pause  # type: ignore
                else:
                    transition = self.state_machine.pause_full_mission  # type: ignore
                break

            if not self.task_status_thread:
                self._run_get_status_thread(
                    status_function=self.state_machine.robot.task_status,
                    function_argument=self.state_machine.current_task.id,
                    thread_name="State Machine Monitor Get Step Status",
                )
            try:
                status: TaskStatus = self.task_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue

            except RobotCommunicationTimeoutException as e:
                task_failed: bool = self._handle_communication_timeout(e)
                if task_failed:
                    status = TaskStatus.Failed
                else:
                    continue

            except RobotTaskStatusException as e:
                self.state_machine.current_task.error_message = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                self.logger.error(
                    f"Monitoring task {self.state_machine.current_task.id[:8]} failed "
                    f"because: {e.error_description}"
                )
                status = TaskStatus.Failed

            except RobotException as e:
                self._set_error_message(e)
                status = TaskStatus.Failed

                self.logger.error(
                    f"Retrieving the status failed because: {e.error_description}"
                )

            if not isinstance(status, TaskStatus):
                self.logger.error(
                    f"Received an invalid status update when monitoring mission. Only TaskStatus is expected."
                )
                break

            if self.state_machine.current_task == None:
                self.state_machine.iterate_current_task()

            self.state_machine.current_task.status = status

            if self._should_upload_inspections():
                get_inspection_thread = ThreadedRequest(
                    self._queue_inspections_for_upload
                )
                get_inspection_thread.start_thread(
                    deepcopy(self.state_machine.current_mission),
                    deepcopy(self.state_machine.current_task),
                    name="State Machine Get Inspections",
                )

            if self.state_machine.run_mission_by_task:
                if self.state_machine.current_task.is_finished():
                    self._report_task_status(self.state_machine.current_task)
                    transition = self.state_machine.task_finished  # type: ignore
                    break
            else:
                if self.state_machine.current_task.is_finished():
                    self._report_task_status(self.state_machine.current_task)
                    self.state_machine.publish_task_status(
                        task=self.state_machine.current_task
                    )

                    self.state_machine.iterate_current_task()
                    if self.state_machine.current_task == None:
                        transition = self.state_machine.full_mission_finished  # type: ignore
                        break

                    # Report and update next task
                    self.state_machine.current_task.update_task_status()
                    self.state_machine.publish_task_status(
                        task=self.state_machine.current_task
                    )

            self.task_status_thread = None
            time.sleep(self.state_machine.sleep_time)

        transition()

    def _run_get_status_thread(
        self, status_function: Callable, function_argument: str, thread_name: str
    ) -> None:
        self.task_status_thread = ThreadedRequest(request_func=status_function)
        self.task_status_thread.start_thread(function_argument, name=thread_name)

    def _queue_inspections_for_upload(
        self, mission: Mission, current_task: InspectionTask
    ) -> None:
        try:
            inspection: Inspection = self.state_machine.robot.get_inspection(
                task=current_task
            )

        except (RobotRetrieveInspectionException, RobotException) as e:
            self._set_error_message(e)
            self.logger.error(
                f"Failed to retrieve inspections because: {e.error_description}"
            )
            return

        if not inspection:
            self.logger.warning(
                f"No inspection data retrieved for task {str(current_task.id)[:8]}"
            )

        inspection.metadata.tag_id = current_task.tag_id

        message: Tuple[Inspection, Mission] = (
            inspection,
            mission,
        )
        self.state_machine.queues.upload_queue.put(message)
        self.logger.info(f"Inspection: {str(inspection.id)[:8]} queued for upload")

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

    def _handle_communication_timeout(
        self, e: RobotCommunicationTimeoutException
    ) -> bool:
        self.state_machine.current_mission.error_message = ErrorMessage(
            error_reason=e.error_reason, error_description=e.error_description
        )
        self.task_status_thread = None
        self.request_status_failure_counter += 1
        self.logger.warning(
            f"Monitoring task {self.state_machine.current_task.id} failed #: "
            f"{self.request_status_failure_counter} failed because: {e.error_description}"
        )

        if (
            self.request_status_failure_counter
            >= self.request_status_failure_counter_limit
        ):
            self.state_machine.current_task.error_message = ErrorMessage(
                error_reason=e.error_reason,
                error_description=e.error_description,
            )
            self.logger.error(
                f"Step will be cancelled after failing to get task status "
                f"{self.request_status_failure_counter} times because: "
                f"{e.error_description}"
            )
            return True

        return False
