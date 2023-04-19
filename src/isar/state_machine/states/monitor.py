import logging
import time
from copy import deepcopy
from typing import Callable, Optional, Sequence, TYPE_CHECKING, Tuple, Union

from injector import inject
from transitions import State

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions import RobotException
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.step import InspectionStep, Step, StepStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine") -> None:
        super().__init__(name="monitor", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine

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
                transition = self.state_machine.pause  # type: ignore
                break

            if not self.step_status_thread:
                if self.state_machine.stepwise_mission:
                    self._run_get_status_thread(
                        status_function=self.state_machine.robot.step_status,
                        thread_name="State Machine Monitor Get Step Status",
                    )
                else:
                    self._run_get_status_thread(
                        status_function=self.state_machine.robot.mission_status,
                        thread_name="State Machine Monitor Get Mission Status",
                    )

            try:
                status: Union[
                    StepStatus, MissionStatus
                ] = self.step_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotException:
                status = StepStatus.Failed

            if self.state_machine.stepwise_mission and isinstance(status, StepStatus):
                self.state_machine.current_step.status = status
            elif isinstance(status, MissionStatus):
                self.state_machine.current_mission.status = status

            if self._should_upload_inspections():
                get_inspections_thread = ThreadedRequest(
                    self._queue_inspections_for_upload
                )
                get_inspections_thread.start_thread(
                    self.state_machine.current_step,
                    name="State Machine Get Inspections",
                )

            if self.state_machine.stepwise_mission:
                if self._step_finished(self.state_machine.current_step):
                    transition = self.state_machine.step_finished  # type: ignore
                    break
            else:
                if self._mission_finished(self.state_machine.current_mission):
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

    def _queue_inspections_for_upload(self, current_step: InspectionStep) -> None:
        try:
            inspections: Sequence[
                Inspection
            ] = self.state_machine.robot.get_inspections(step=current_step)
        except Exception as e:
            if self.state_machine.stepwise_mission:
                self.logger.error(
                    f"Error getting inspections for step "
                    f"{str(current_step.id)[:8]}: {e}"
                )
            else:
                self.logger.error(
                    f"Error getting inspections for mission "
                    f"{str(self.state_machine.current_mission.id)[:8]}: {e}"
                )
            return

        if not inspections:
            self.logger.warning(
                f"No inspection data retrieved for step {str(current_step.id)[:8]}"
            )

        # A deepcopy is made to freeze the metadata before passing it to another thread
        # through the queue
        mission_metadata: MissionMetadata = deepcopy(
            self.state_machine.current_mission_metadata
        )

        for inspection in inspections:
            inspection.metadata.tag_id = current_step.tag_id

            message: Tuple[Inspection, MissionMetadata] = (
                inspection,
                mission_metadata,
            )
            self.state_machine.queues.upload_queue.put(message)
            self.logger.info(f"Inspection: {str(inspection.id)[:8]} queued for upload")

    def _step_finished(self, step: Step) -> bool:
        finished: bool = False
        if step.status == StepStatus.Failed:
            self.logger.warning(f"Step: {str(step.id)[:8]} failed")
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
        if self.state_machine.stepwise_mission:
            step: Step = self.state_machine.current_step
            return (
                self._step_finished(step)
                and step.status == StepStatus.Successful
                and isinstance(step, InspectionStep)
            )
        else:
            mission_status: MissionStatus = self.state_machine.current_mission.status
            if (
                mission_status == MissionStatus.Successful
                or mission_status == MissionStatus.PartiallySuccessful
            ):
                return True
            return False
