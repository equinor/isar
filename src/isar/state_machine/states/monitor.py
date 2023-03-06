import logging
import time
from copy import deepcopy
from typing import Callable, Optional, Sequence, TYPE_CHECKING, Tuple

from injector import inject
from transitions import State

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from robot_interface.models.exceptions import RobotException
from robot_interface.models.inspection.inspection import Inspection
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
                self.step_status_thread = ThreadedRequest(
                    self.state_machine.robot.step_status
                )
                self.step_status_thread.start_thread(
                    name="State Machine Monitor Current Step"
                )

            try:
                step_status: StepStatus = self.step_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotException:
                step_status = StepStatus.Failed

            self.state_machine.current_step.status = step_status

            if self._step_finished(step=self.state_machine.current_step):
                get_inspections_thread = ThreadedRequest(self._process_finished_step)
                get_inspections_thread.start_thread(
                    self.state_machine.current_step,
                    name="State Machine Get Inspections",
                )
                transition = self.state_machine.step_finished  # type: ignore
                break

            self.step_status_thread = None
            time.sleep(self.state_machine.sleep_time)

        transition()

    def _queue_inspections_for_upload(self, current_step: InspectionStep) -> None:
        try:
            inspections: Sequence[
                Inspection
            ] = self.state_machine.robot.get_inspections(step=current_step)
        except Exception as e:
            self.logger.error(
                f"Error getting inspections for step {str(current_step.id)[:8]}: {e}"
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

    def _process_finished_step(self, step: Step) -> None:
        if step.status == StepStatus.Successful and isinstance(step, InspectionStep):
            self._queue_inspections_for_upload(current_step=step)
