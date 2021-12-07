import logging
from typing import List, TYPE_CHECKING, Union

from injector import inject
from transitions import State

from isar.storage.storage_service import StorageService
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.inspection.inspection import Inspection, TimeIndexedPose
from robot_interface.models.mission import InspectionTask
from robot_interface.models.exceptions import RobotException

from isar.services.coordinates.transformation import Transformation

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Cancel(State):
    @inject
    def __init__(
        self,
        state_machine: "StateMachine",
        transform: Transformation,
        storage_service: StorageService,
    ):
        super().__init__(name="cancel", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.storage_service = storage_service
        self.logger = logging.getLogger("state_machine")
        self.transform = transform

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.current_state}")

        inspection_tasks: List[InspectionTask] = [
            task
            for task in self.state_machine.current_mission.tasks
            if isinstance(task, InspectionTask)
        ]

        inspections: List[Inspection] = []
        for task in inspection_tasks:
            try:
                results: List[Inspection] = self.state_machine.robot.get_inspections(
                    task
                )
            except RobotException as e:
                self.logger.error(e)
                continue

            for result in results:
                result.metadata.tag_id = task.tag_id
                self._transform_poses_to_asset_frame(result.metadata.time_indexed_pose)
                inspections.append(result)
                self.storage_service.store(
                    self.state_machine.current_mission.id,
                    result,
                )

        if inspections:
            self.storage_service.store_metadata(
                mission=self.state_machine.current_mission, inspections=inspections
            )

        self._log_task_status()
        next_state = self.state_machine.reset_state_machine()
        self.state_machine.to_next_state(next_state)

    def stop(self):
        self._log_state_transitions()

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

    def _log_state_transitions(self):
        state_transitions: str = ", ".join(
            [
                f"\n  {transition}" if (i + 1) % 10 == 0 else f"{transition}"
                for i, transition in enumerate(
                    list(self.state_machine.transitions_list)
                )
            ]
        )

        self.logger.info(f"State transitions:\n  {state_transitions}")

    def _log_task_status(self):
        task_status: str = "\n".join(
            [
                f"{i:>3}  {task.name:<25}" f" -- {task.status} "
                for i, task in enumerate(self.state_machine.current_mission.tasks)
            ]
        )
        self.logger.info(f"Mission task status:\n{task_status}")
