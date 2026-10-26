from typing import Self

from pydantic import BaseModel, Field, model_validator

from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from robot_interface.models.mission.task import TASKS


class Mission(BaseModel):
    id: str = Field(frozen=True)
    tasks: list[TASKS] = Field(default_factory=list, frozen=True)
    name: str = Field(frozen=True)
    robot_mission_id: str | None = Field(default=None, frozen=True)
    status: MissionStatus = MissionStatus.NotStarted
    error_message: ErrorMessage | None = Field(default=None)

    @model_validator(mode="after")
    def validate_stored_mission(self) -> Self:
        if self.robot_mission_id is not None:
            if not self.robot_mission_id.strip():
                raise ValueError("Robot mission ID must not be blank")
            if self.tasks:
                raise ValueError("Stored robot missions cannot contain tasks")
        return self

    def _get_unfinished_tasks(self) -> list[TASKS]:
        return [
            t
            for t in self.tasks
            if t.status
            not in [
                TaskStatus.Failed,
                TaskStatus.Successful,
                TaskStatus.PartiallySuccessful,
            ]
        ]
