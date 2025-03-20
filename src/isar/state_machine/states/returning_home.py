import logging
from queue import Queue
from typing import TYPE_CHECKING, Optional

from transitions import State

from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queue_utils import (
    check_for_event,
    check_for_event_without_consumption,
    trigger_event,
)
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import TaskStatus
from robot_interface.models.mission.task import Task

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturningHome(State):
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="returning_home", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine

        self.logger = logging.getLogger("state_machine")
        self.events = self.state_machine.events

        self.awaiting_task_status: bool = False
        self.signal_state_machine_to_stop = state_machine.signal_state_machine_to_stop

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        self.state_machine.mission_ongoing = False
        return

    def _check_and_handle_stop_mission_event(self, event: Queue) -> bool:
        if check_for_event(event):
            self.state_machine.stop()  # type: ignore
            return True
        return False

    def _check_and_handle_mission_started_event(self, event: Queue) -> bool:
        if self.state_machine.mission_ongoing:
            return False

        if check_for_event(event):
            self.state_machine.mission_ongoing = True
            return False

        return True

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

            self.state_machine.iterate_current_task()
            if self.state_machine.current_task is None:
                if status != TaskStatus.Successful:
                    self.state_machine.return_home_failed()  # type: ignore
                self.state_machine.returned_home()  # type: ignore
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
        while True:
            if self.signal_state_machine_to_stop.is_set():
                self.logger.info(
                    "Stopping state machine from %s state", self.__class__.__name__
                )
                break

            if self._check_and_handle_stop_mission_event(
                self.events.api_requests.stop_mission.input
            ):
                break

            if self._check_and_handle_mission_started_event(
                self.events.robot_service_events.mission_started
            ):
                continue

            if self._check_and_handle_task_status_event(
                self.events.robot_service_events.task_status_updated
            ):
                break

            if self._check_and_handle_start_mission_event(
                self.events.api_requests.start_mission.input
            ):
                break

            if self._check_and_handle_mission_failed_event(
                self.events.robot_service_events.mission_failed
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

    def _report_task_status(self, task: Task) -> None:
        if task.status == TaskStatus.Failed:
            self.logger.warning(
                f"Task: {str(task.id)[:8]} was reported as failed by the robot"
            )
        elif task.status == TaskStatus.Successful:
            self.logger.info(
                f"{type(task).__name__} task: {str(task.id)[:8]} completed"
            )
