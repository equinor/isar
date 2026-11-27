from pydantic import BaseModel, Field


class Position2D(BaseModel):
    x: float = Field(frozen=True)
    y: float = Field(frozen=True)


class Polygon(BaseModel):
    zmin: float = Field(frozen=True)
    zmax: float = Field(frozen=True)
    positions: list[Position2D] = Field(default_factory=list, frozen=True)
