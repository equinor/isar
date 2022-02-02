from typing import Optional

from pydantic import BaseModel


class StartResponse(BaseModel):
    message: str
    started: bool
    mission_id: Optional[str] = None


class StopResponse(BaseModel):
    message: str
    stopped: bool
