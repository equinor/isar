from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


@dataclass
class Joints:
    j1: Optional[float] = None
    j2: Optional[float] = None
    j3: Optional[float] = None
    j4: Optional[float] = None
    j5: Optional[float] = None
    validate_constraints: bool = True

    def __post_init__(self):
        if self.validate_constraints and not joints_within_constraints(self):
            raise ValueError("Joint values are not valid")


def joints_within_constraints(joints: Any) -> bool:
    is_valid = True
    if (
        joints.j1 is None
        or joints.j1 < Constraints.j1_lower.value
        or joints.j1 > Constraints.j1_upper.value
    ):
        raise ValueError(f"j1 = {joints.j1} is outside the valid range")
    if (
        joints.j2 is None
        or joints.j2 < Constraints.j2_lower.value
        or joints.j2 > Constraints.j2_upper.value
    ):
        raise ValueError(f"j2 = {joints.j2} is outside the valid range")
    return is_valid


class Constraints(Enum):
    j1_upper: float = 5.818
    j1_lower: float = 0.022
    j2_lower: float = 0.022
    j2_upper: float = 3.348
