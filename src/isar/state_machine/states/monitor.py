import logging
import time
from typing import TYPE_CHECKING, Sequence, Tuple

from injector import inject
from transitions import State

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions import RobotException
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission import InspectionTask, Task, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine"):
        super().__init__(name="monitor", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine

        self.logger = logging.getLogger("state_machine")

        self.iteration_counter: int = 0
        self.log_interval = 20

        self.task_status_thread = None

    def start(self):
        self.state_machine.update_state()
        self._run()

    def stop(self):
        if self.state_machine.mqtt_client:
            self.state_machine.publish_task_status()
            self.state_machine.publish_mission()

        self.iteration_counter = 0
        if self.task_status_thread:
            self.task_status_thread.wait_for_thread()
        self.task_status_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            if not self.state_machine.mission_in_progress:
                next_state = States.Finalize
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()
            if not self.task_status_thread:
                self.task_status_thread = ThreadedRequest(
                    self.state_machine.robot.task_status
                )
                self.task_status_thread.start_thread()

            try:
                task_status: TaskStatus = self.task_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotException:
                task_status = TaskStatus.Unexpected

            self.state_machine.current_task.status = task_status

            if self._task_finished(task=self.state_machine.current_task):
                next_state = self._process_finished_task(
                    task=self.state_machine.current_task
                )
                break
            else:
                self.task_status_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)

    def _queue_inspections_for_upload(self, current_task: InspectionTask):
        try:
            inspections: Sequence[
                Inspection
            ] = self.state_machine.robot.get_inspections(task=current_task)
        except Exception as e:
            self.logger.error(
                f"Error getting inspections for task {str(current_task.id)[:8]}: {e}"
            )
            return

        mission_metadata: MissionMetadata = self.state_machine.current_mission.metadata
        for inspection in inspections:
            inspection.metadata.tag_id = current_task.tag_id

            message: Tuple[Inspection, MissionMetadata] = (
                inspection,
                mission_metadata,
            )
            self.state_machine.queues.upload_queue.put(message)
            self.logger.info(f"Inspection: {str(inspection.id)[:8]} queued for upload")

    def _task_finished(self, task: Task) -> bool:
        finished: bool = False
        if task.status == TaskStatus.Unexpected:
            self.logger.error("Task status returned an unexpected status string")
        elif task.status == TaskStatus.Failed:
            self.logger.warning(f"Task: {str(task.id)[:8]} failed")
            finished = True
        elif task.status == TaskStatus.Completed:
            self.logger.info(
                f"{type(task).__name__} task: {str(task.id)[:8]} completed"
            )
            finished = True
        return finished

    def _process_finished_task(self, task: Task) -> State:
        if task.status == TaskStatus.Completed and isinstance(task, InspectionTask):
            self._queue_inspections_for_upload(current_task=task)

        return States.InitiateTask
