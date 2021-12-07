import logging
import time
from typing import TYPE_CHECKING, Any, List, Sequence, Union

from injector import inject
from transitions import State

from isar.services.coordinates.transformation import Transformation
from isar.services.utilities.threaded_request import (
    ThreadedRequest,
    ThreadedRequestNotFinishedError,
    ThreadedRequestUnexpectedError,
)
from isar.state_machine.states_enum import States
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.inspection.inspection import Inspection, TimeIndexedPose
from robot_interface.models.mission.task import Task

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Collect(State):
    @inject
    def __init__(
        self,
        state_machine: "StateMachine",
        transform: Transformation,
    ):
        super().__init__(name="collect", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.transform = transform

        self.collect_thread = None

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.current_state}")

        self._run()

    def stop(self):
        if self.collect_thread:
            self.collect_thread.wait_for_thread()
        self.collect_thread = None

    def _run(self):
        while True:
            if self.state_machine.should_stop_mission():
                self.state_machine.stop_mission()

            if self.state_machine.should_send_status():
                self.state_machine.send_status()

            if not self.collect_thread:
                current_task: Task = self.state_machine.current_task
                self.collect_thread = ThreadedRequest(
                    self.state_machine.robot.get_inspection_references
                )
                self.collect_thread.start_thread(current_task)

            try:
                inspections: Sequence[Inspection] = self.collect_thread.get_output()
            except ThreadedRequestNotFinishedError:
                time.sleep(self.state_machine.sleep_time)
                continue
            except ThreadedRequestUnexpectedError:
                inspections: Sequence[Inspection] = []

            for inspection_ref in inspections:
                inspection_ref.metadata.tag_id = current_task.tag_id  # type: ignore

                self._transform_results_to_asset_frame(
                    time_indexed_pose=inspection_ref.metadata.time_indexed_pose
                )

            self.state_machine.current_mission.inspections.extend(inspections)

            next_state: States = States.Send
            self.collect_thread = None
            break

        self.state_machine.to_next_state(next_state)

    def _transform_results_to_asset_frame(
        self, time_indexed_pose: Union[TimeIndexedPose, List[TimeIndexedPose]]
    ):
        if isinstance(time_indexed_pose, TimeIndexedPose):
            time_indexed_pose.pose = self.transform.transform_pose(
                pose=time_indexed_pose.pose,
                to_=Frame.Asset,
            )
        elif isinstance(time_indexed_pose, list):
            for indexed_pose in time_indexed_pose:
                indexed_pose.pose = self.transform.transform_pose(
                    pose=indexed_pose.pose,
                    to_=Frame.Asset,
                )
