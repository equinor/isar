from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from robot_interface.models.mission.status import StepStatus, TaskStatus
from robot_interface.models.mission.step import (
    DriveToPose,
    InspectionStep,
    MotionStep,
    STEPS,
    Step,
)
from robot_interface.utilities.uuid_string_factory import uuid4_string


@dataclass
class Task:
    steps: List[STEPS]
    status: TaskStatus = field(default=TaskStatus.NotStarted, init=False)
    tag_id: Optional[str] = field(default=None)
    id: str = field(default_factory=uuid4_string, init=True)
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
                # considered as failed
                return True

            elif (step.status is StepStatus.Failed) and isinstance(
                step, InspectionStep
            ):
                # It should be possible to perform several inspections per task. If
                # one out of many inspections fail the task is considered as
                # partially successful.
                continue

            elif step.status is StepStatus.Successful:
                # The task is complete once all steps are completed
                continue
            else:
                # Not all steps have been completed yet
                return False

        return True

    def update_task_status(self) -> None:
        for step in self.steps:
            if step.status is StepStatus.Failed and isinstance(step, MotionStep):
                self.status = TaskStatus.Failed
                return

            elif (step.status is StepStatus.Failed) and isinstance(
                step, InspectionStep
            ):
                self.status = TaskStatus.PartiallySuccessful
                continue

            elif step.status is StepStatus.Successful:
                continue

        if self.status is not TaskStatus.PartiallySuccessful:
            self.status = TaskStatus.Successful

        elif self._all_inspection_steps_failed():
            self.status = TaskStatus.Failed

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
