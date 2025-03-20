from typing import List, Optional

from alitra import Pose
from pydantic import BaseModel, Field

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import TASKS, TaskTypes
from robot_interface.utilities.uuid_string_factory import uuid4_string


class Mission(BaseModel):
    id: str = Field(default_factory=uuid4_string, frozen=True)
    tasks: List[TASKS] = Field(default_factory=list, frozen=True)
    name: str = Field(frozen=True)
    start_pose: Optional[Pose] = Field(default=None, frozen=True)
    status: MissionStatus = MissionStatus.NotStarted
    error_message: Optional[ErrorMessage] = Field(default=None)

    def _is_return_to_home_mission(self) -> bool:
        if len(self.tasks) != 1:
            return False
        if self.tasks[0].type != TaskTypes.ReturnToHome:
            return False
        return True
