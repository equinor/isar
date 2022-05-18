from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel


class StartFailedResponse(BaseModel):
    message: str


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


class StopFailedResponse(BaseModel):
    message: str
