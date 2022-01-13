import logging
import time
from typing import List, Sequence, TYPE_CHECKING, Tuple, Union

from injector import inject
from transitions import State

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.coordinates.transformation import Transformation
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions import RobotException
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.inspection.inspection import Inspection, TimeIndexedPose
from robot_interface.models.mission import InspectionTask, TaskStatus

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Monitor(State):
    @inject
    def __init__(self, state_machine: "StateMachine", transform: Transformation):
        super().__init__(name="monitor", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.transform: Transformation = transform

        self.logger = logging.getLogger("state_machine")

        self.iteration_counter: int = 0
        self.log_interval = 20

        self.task_status_thread = None

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.current_state}")

        self._run()

    def stop(self):
        self.iteration_counter = 0
        if self.task_status_thread:
            self.task_status_thread.wait_for_thread()
        self.task_status_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            if not self.state_machine.mission_in_progress:
                next_state = States.Cancel
                break

            if self.state_machine.should_send_status():
                self.state_machine.send_status()
            if not self.task_status_thread:
                self.task_status_thread = ThreadedRequest(
                    self.state_machine.robot.task_status
                )
                self.task_status_thread.start_thread()

            try:
                task_status = self.task_status_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except RobotException:
                task_status = TaskStatus.Unexpected

            self.state_machine.current_task.status = task_status

            if self._task_completed(task_status=self.state_machine.current_task.status):
                if isinstance(self.state_machine.current_task, InspectionTask):
                    inspections: Sequence[
                        Inspection
                    ] = self.state_machine.robot.get_inspections(
                        task=self.state_machine.current_task
                    )

                    mission_metadata: MissionMetadata = (
                        self.state_machine.current_mission.metadata
                    )
                    for inspection in inspections:
                        inspection.metadata.tag_id = (
                            self.state_machine.current_task.tag_id
                        )
                        self._transform_poses_to_asset_frame(
                            time_indexed_pose=inspection.metadata.time_indexed_pose
                        )

                        message: Tuple[Inspection, MissionMetadata] = (
                            inspection,
                            mission_metadata,
                        )
                        self.state_machine.queues.upload_queue.put(message)

                next_state = States.Send
                break
            else:
                self.task_status_thread = None
                time.sleep(self.state_machine.sleep_time)

        self.state_machine.to_next_state(next_state)

    def _task_completed(self, task_status: TaskStatus) -> bool:

        if task_status == TaskStatus.Unexpected:
            self.logger.error("Task status returned an unexpected status string")
        elif task_status == TaskStatus.Failed:
            self.logger.warning("Task failed...")
            return True
        elif task_status == TaskStatus.Completed:
            return True
        return False

    def _transform_poses_to_asset_frame(
        self, time_indexed_pose: Union[TimeIndexedPose, List[TimeIndexedPose]]
    ):
        if isinstance(time_indexed_pose, TimeIndexedPose):
            time_indexed_pose = [time_indexed_pose]

        for indexed_pose in time_indexed_pose:
            indexed_pose.pose = self.transform.transform_pose(
                pose=indexed_pose.pose,
                to_=Frame.Asset,
            )
