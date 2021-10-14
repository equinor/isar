import logging
from typing import TYPE_CHECKING, List, Sequence, Union

from injector import inject
from transitions import State

from isar.services.coordinates.transformation import Transformation
from isar.state_machine.states_enum import States
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.inspection.inspection import Inspection, TimeIndexedPose

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Collect(State):
    @inject
    def __init__(
        self,
        state_machine: "StateMachine",
        transform: Transformation,
    ):
        super().__init__(name="collect", on_enter=self.start)
        self.state_machine: "StateMachine" = state_machine
        self.logger = logging.getLogger("state_machine")
        self.transform = transform

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.status.current_state}")

        next_state = self._collect_results()
        self.state_machine.to_next_state(next_state)

    def _collect_results(self) -> States:
        instance_id = self.state_machine.status.current_mission_instance_id
        current_step = self.state_machine.status.current_mission_step

        inspections: Sequence[
            Inspection
        ] = self.state_machine.robot.get_inspection_references(
            vendor_mission_id=instance_id,
            current_step=current_step,
        )
        for inspection_ref in inspections:
            inspection_ref.metadata.tag_id = current_step.tag_id  # type: ignore

            self._transform_results_to_asset_frame(
                time_indexed_pose=inspection_ref.metadata.time_indexed_pose
            )

        self.state_machine.status.mission_schedule.inspections.extend(inspections)

        return States.Send

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
