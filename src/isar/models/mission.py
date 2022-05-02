from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, List, Union
from uuid import UUID, uuid4

from isar.config.settings import settings
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.mission import (
    InspectionStep,
    MotionStep,
    STEPS,
    Step,
    StepStatus,
)


@dataclass
class Task:
    steps: List[STEPS]
    status: StepStatus = field(default=StepStatus.NotStarted, init=False)
    id: UUID = field(default_factory=uuid4, init=False)
    _iterator: Iterator = None

    def next_step(self) -> Step:
        return self._iterator.__next__()

    def is_finished(self) -> bool:
        for step in self.steps:
            if step.status is StepStatus.Failed and isinstance(step, MotionStep):
                # One motion step has failed meaning the task as a whole should be
                # aborted
                self.status = StepStatus.Failed
                return True

            elif (step.status is StepStatus.Failed) and isinstance(
                step, InspectionStep
            ):
                # It should be possible to perform several inspections per task. If
                # one out of many inspections fail the task is considered as
                # partially successful.
                self.status = StepStatus.PartiallySuccessful
                continue

            elif step.status is StepStatus.Completed:
                # The task is complete once all steps are completed
                continue
            else:
                # Not all steps have been completed yet
                return False

        # Check if the task has been marked as partially successful by having one or
        # more inspection steps fail
        if self.status is not StepStatus.PartiallySuccessful:
            # All steps have been completed
            self.status = StepStatus.Completed

        # Set the task to failed if all inspection steps failed
        elif self._all_inspection_steps_failed():
            self.status = StepStatus.Failed

        return True

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


@dataclass
class Mission:
    tasks: List[Task]
    id: Union[UUID, int, str, None] = None
    metadata: MissionMetadata = None
    _iterator: Iterator = None

    def next_task(self) -> Task:
        return self._iterator.__next__()

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

        if self._iterator is None:
            self._iterator = iter(self.tasks)
