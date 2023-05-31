from dataclasses import dataclass
from typing import Optional

from alitra import Pose


@dataclass
class InitializeParams:
    initial_pose: Optional[Pose] = None
