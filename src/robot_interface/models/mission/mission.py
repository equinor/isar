from dataclasses import dataclass, field
from typing import List, Optional

from alitra import Pose

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import TASKS
from robot_interface.utilities.uuid_string_factory import uuid4_string


@dataclass
class Mission:
    tasks: List[TASKS]
    id: str = field(default_factory=uuid4_string, init=True)
    name: str = ""
    start_pose: Optional[Pose] = None
    dock: Optional[bool] = None
    undock: Optional[bool] = None
    status: MissionStatus = MissionStatus.NotStarted
    error_message: Optional[ErrorMessage] = field(default=None, init=False)

    def _set_unique_id(self) -> None:
        self.id: str = uuid4_string()

    def __post_init__(self) -> None:
        if self.id is None:
            self._set_unique_id()
