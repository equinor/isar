from typing import List
from uuid import uuid4

from alitra import Pose
from pydantic import BaseModel, Field

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TASKS, ReturnToHome, TaskTypes


class Mission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), frozen=True)
    tasks: List[TASKS] = Field(default_factory=list, frozen=True)
    name: str = Field(frozen=True)
    start_pose: Pose | None = Field(default=None, frozen=True)
    status: MissionStatus = MissionStatus.NotStarted
    error_message: ErrorMessage | None = Field(default=None)

    def _is_return_to_home_mission(self) -> bool:
        if len(self.tasks) != 1:
            return False
        if self.tasks[0].type != TaskTypes.ReturnToHome:
            return False
        return True

    def _get_unfinished_tasks(self) -> List[TASKS]:
        return list(
            filter(
                lambda task: task.status
                not in [
                    TaskStatus.Failed,
                    TaskStatus.Successful,
                    TaskStatus.PartiallySuccessful,
                ],
                self.tasks,
            )
        )


class ReturnHomeMission(Mission):
    tasks: List[TASKS] = Field(default_factory=lambda: [ReturnToHome()])
    name: str = "Return Home"
