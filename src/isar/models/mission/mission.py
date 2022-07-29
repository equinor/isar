from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, List, Optional, Union
from uuid import UUID, uuid4

from isar.config.settings import settings
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.mission import (
    InspectionStep,
    STEPS,
    MotionStep,
    Step,
    StepStatus,
)
from robot_interface.models.mission.step import DriveToPose

from .status import MissionStatus, TaskStatus


@dataclass
class Task:
    steps: List[STEPS]
    status: TaskStatus = field(default=TaskStatus.NotStarted, init=False)
    tag_id: Optional[str] = field(default=None)
    id: UUID = field(default_factory=uuid4, init=False)
    _iterator: Iterator = None

    def next_step(self) -> Step:
        step: Step = next(self._iterator)
        while step.status != StepStatus.NotStarted:
            step = next(self._iterator)
        return step

    def is_finished(self) -> bool:
        for step in self.steps:
            if step.status is StepStatus.Failed and isinstance(step, MotionStep):
                # One motion step has failed meaning the task as a whole should be
                # aborted
                self.status = TaskStatus.Failed
                return True

            elif (step.status is StepStatus.Failed) and isinstance(
                step, InspectionStep
            ):
                # It should be possible to perform several inspections per task. If
                # one out of many inspections fail the task is considered as
                # partially successful.
                self.status = TaskStatus.PartiallySuccessful
                continue

            elif step.status is StepStatus.Successful:
                # The task is complete once all steps are completed
                continue
            else:
                # Not all steps have been completed yet
                return False

        # Check if the task has been marked as partially successful by having one or
        # more inspection steps fail
        if self.status is not TaskStatus.PartiallySuccessful:
            # All steps have been completed
            self.status = TaskStatus.Successful

        # Set the task to failed if all inspection steps failed
        elif self._all_inspection_steps_failed():
            self.status = TaskStatus.Failed

        return True

    def reset_task(self):
        for step in self.steps:
            if isinstance(step, DriveToPose):
                step.status = StepStatus.NotStarted
            elif (
                isinstance(step, InspectionStep)
                and step.status == StepStatus.InProgress
            ):
                step.status = StepStatus.NotStarted
        self._iterator = iter(self.steps)

    def _all_inspection_steps_failed(self) -> bool:
        for step in self.steps:
            if isinstance(step, MotionStep):
                continue
            elif step.status is not StepStatus.Failed:
                return False

        return True

    def __post_init__(self) -> None:
        if self._iterator is None:
            self._iterator = iter(self.steps)

    def api_response_dict(self):
        return {
            "id": self.id,
            "tag_id": self.tag_id,
            "steps": list(
                map(lambda x: {"id": x.id, "type": x.__class__.__name__}, self.steps)
            ),
        }


@dataclass
class Mission:
    tasks: List[Task]
    id: Union[UUID, int, str, None] = None
    status: MissionStatus = MissionStatus.NotStarted
    metadata: MissionMetadata = None

    def set_unique_id_and_metadata(self) -> None:
        self._set_unique_id()
        self.metadata = MissionMetadata(mission_id=self.id)

    def _set_unique_id(self) -> None:
        plant_short_name: str = settings.PLANT_SHORT_NAME
        robot_id: str = settings.ROBOT_ID
        now: datetime = datetime.utcnow()
        self.id = (
            f"{plant_short_name.upper()}{robot_id.upper()}"
            f"{now.strftime('%d%m%Y%H%M%S%f')[:-3]}"
        )

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()

        if self.metadata is None:
            self.metadata = MissionMetadata(mission_id=self.id)

    def api_response_dict(self) -> dict:
        return {
            "id": self.id,
            "tasks": [task.api_response_dict() for task in self.tasks],
        }
