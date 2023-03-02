from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, List, Optional, Union
from uuid import UUID, uuid4

from robot_interface.models.mission import (
    InspectionStep,
    MotionStep,
    STEPS,
    Step,
    StepStatus,
)
from robot_interface.models.mission.step import DriveToPose

from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import Task


@dataclass
class Mission:
    tasks: List[Task]
    id: Union[UUID, int, str, None] = None
    status: MissionStatus = MissionStatus.NotStarted

    def _set_unique_id(self) -> None:
        self.id: UUID = uuid4()

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()
