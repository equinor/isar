import logging
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Callable, Optional, Sequence, Tuple, Union

from injector import inject
from transitions import State

from isar.config.settings import settings
from isar.mission_planner.task_selector_interface import TaskSelectorStop
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotCommunicationTimeoutException,
    RobotException,
    RobotMissionStatusException,
    RobotRetrieveInspectionException,
    RobotStepStatusException,
)
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.step import InspectionStep, Step, StepStatus

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
        self.step_status_thread: Optional[ThreadedRequest] = None

    def start(self) -> None:
        self.state_machine.update_state()
        self._run()

    def stop(self) -> None:
        if self.step_status_thread:
            self.step_status_thread.wait_for_thread()
        self.step_status_thread = None

    def _run(self) -> None:
        transition: Callable
        while True:
            if self.state_machine.should_stop_mission():
                transition = self.state_machine.stop  # type: ignore
                break

            if self.state_machine.should_pause_mission():
                if self.state_machine.stepwise_mission:
                    transition = self.state_machine.pause  # type: ignore
                else:
                    transition = self.state_machine.pause_full_mission  # type: ignore
                break

            if not self.step_status_thread:
                self._run_get_status_thread(
                    status_function=self.state_machine.robot.step_status,
                    thread_name="State Machine Monitor Get Step Status",
                )
            try:
                status: Union[StepStatus, MissionStatus] = (
                    self.step_status_thread.get_output()
                )
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue

            except RobotCommunicationTimeoutException as e:
                self.state_machine.current_mission.error_message = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                self.step_status_thread = None
                self.request_status_failure_counter += 1
                self.logger.warning(
                    f"Monitoring step {self.state_machine.current_step.id} failed #: "
                    f"{self.request_status_failure_counter} failed because: {e.error_description}"
                )

                if (
                    self.request_status_failure_counter
                    >= self.request_status_failure_counter_limit
                ):
                    self.state_machine.current_step.error_message = ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    )
                    self.logger.error(
                        f"Step will be cancelled after failing to get step status "
                        f"{self.request_status_failure_counter} times because: "
                        f"{e.error_description}"
                    )
                    status = StepStatus.Failed
                else:
                    continue

            except RobotStepStatusException as e:
                self.state_machine.current_step.error_message = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                self.logger.error(
                    f"Monitoring step {self.state_machine.current_step.id[:8]} failed "
                    f"because: {e.error_description}"
                )
                status = StepStatus.Failed

            except RobotMissionStatusException as e:
                self.state_machine.current_mission.error_message = ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                )
                self.logger.error(
                    f"Monitoring mission {self.state_machine.current_mission.id} "
                    f"failed because: {e.error_description}"
                )
                status = MissionStatus.Failed

            except RobotException as e:
                self._set_error_message(e)
                status = StepStatus.Failed

                self.logger.error(
                    f"Retrieving the status failed because: {e.error_description}"
                )

            if isinstance(status, StepStatus):
                self.state_machine.current_step.status = status
            elif isinstance(status, MissionStatus):
                self.state_machine.current_mission.status = status
                self.logger.error(
                    f"Received an invalid status update when monitoring mission. Only StepStatus is expected."
                )

            if self._should_upload_inspections():
                get_inspections_thread = ThreadedRequest(
                    self._queue_inspections_for_upload
                )
                get_inspections_thread.start_thread(
                    deepcopy(self.state_machine.current_mission),
                    deepcopy(self.state_machine.current_step),
                    name="State Machine Get Inspections",
                )

            if self.state_machine.stepwise_mission:
                if self._step_finished(self.state_machine.current_step):
                    transition = self.state_machine.step_finished  # type: ignore
                    break
            else:
                if isinstance(status, StepStatus):
                    if self._step_finished(self.state_machine.current_step):
                        self.state_machine.update_current_task()
                        if self.state_machine.current_task == None:
                            transition = self.state_machine.full_mission_finished  # type: ignore
                            break
                        self.state_machine.update_current_step()
                        self.state_machine.current_task.update_task_status()
                    else:  # If not all steps are done
                        self.state_machine.current_task.status = TaskStatus.InProgress

                    self.state_machine.publish_task_status(
                        self.state_machine.current_task
                    )
                    if self.state_machine.current_task.status == TaskStatus.Successful:
                        try:
                            self.state_machine.current_task = (
                                self.state_machine.task_selector.next_task()
                            )
                        except TaskSelectorStop:
                            # Indicates that all tasks are finished
                            self.state_machine.current_task = None
                            transition = self.state_machine.full_mission_finished  # type: ignore
                            break
                        self.state_machine.update_current_step()
                elif self._mission_finished(self.state_machine.current_mission):
                    transition = self.state_machine.full_mission_finished  # type: ignore
                    break

            self.step_status_thread = None
            time.sleep(self.state_machine.sleep_time)

        transition()

    def _run_get_status_thread(
        self, status_function: Callable, thread_name: str
    ) -> None:
        self.step_status_thread = ThreadedRequest(request_func=status_function)
        self.step_status_thread.start_thread(name=thread_name)

    def _queue_inspections_for_upload(
        self, mission: Mission, current_step: InspectionStep
    ) -> None:
        try:
            inspections: Sequence[Inspection] = (
                self.state_machine.robot.get_inspections(step=current_step)
            )

        except (RobotRetrieveInspectionException, RobotException) as e:
            self._set_error_message(e)
            self.logger.error(
                f"Failed to retrieve inspections because: {e.error_description}"
            )
            return

        if not inspections:
            self.logger.warning(
                f"No inspection data retrieved for step {str(current_step.id)[:8]}"
            )

        for inspection in inspections:
            inspection.metadata.tag_id = current_step.tag_id

            message: Tuple[Inspection, Mission] = (
                inspection,
                mission,
            )
            self.state_machine.queues.upload_queue.put(message)
            self.logger.info(f"Inspection: {str(inspection.id)[:8]} queued for upload")

    def _step_finished(self, step: Step) -> bool:
        finished: bool = False
        if step.status == StepStatus.Failed:
            self.logger.warning(
                f"Step: {str(step.id)[:8]} was reported as failed by the robot"
            )
            finished = True
        elif step.status == StepStatus.Successful:
            self.logger.info(
                f"{type(step).__name__} step: {str(step.id)[:8]} completed"
            )
            finished = True
        return finished

    @staticmethod
    def _mission_finished(mission: Mission) -> bool:
        if (
            mission.status == MissionStatus.Successful
            or mission.status == MissionStatus.PartiallySuccessful
            or mission.status == MissionStatus.Failed
        ):
            return True
        return False

    def _should_upload_inspections(self) -> bool:
        step: Step = self.state_machine.current_step
        return (
            self._step_finished(step)
            and step.status == StepStatus.Successful
            and isinstance(step, InspectionStep)
        )

    def _set_error_message(self, e: RobotException) -> None:
        error_message: ErrorMessage = ErrorMessage(
            error_reason=e.error_reason, error_description=e.error_description
        )
        self.state_machine.current_step.error_message = error_message
