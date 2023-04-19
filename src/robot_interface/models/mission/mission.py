from dataclasses import dataclass, field
from typing import List

from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import Task
from robot_interface.utilities.uuid_string_factory import uuid4_string


@dataclass
class Mission:
    tasks: List[Task]
    id: str = field(default_factory=uuid4_string, init=True)
    status: MissionStatus = MissionStatus.NotStarted

    def _set_unique_id(self) -> None:
        self.id: str = uuid4_string()

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()
