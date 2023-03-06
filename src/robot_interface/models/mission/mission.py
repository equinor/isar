from dataclasses import dataclass
from typing import List, Union
from uuid import UUID, uuid4

from robot_interface.models.mission import MissionStatus, Task


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
