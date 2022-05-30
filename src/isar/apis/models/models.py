from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel


class StepResponse(BaseModel):
    id: UUID
    type: str


class TaskResponse(BaseModel):
    id: UUID
    tag_id: Optional[str]
    steps: List[StepResponse]


class StartMissionResponse(BaseModel):
    id: Union[UUID, int, str, None]
    tasks: List[TaskResponse]


class ApiPose(BaseModel):
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float
