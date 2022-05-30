from dataclasses import dataclass
from email.policy import default

from alitra import Pose
from pyparsing import Optional


@dataclass
class InitializeParams:
    initial_pose: Optional[Pose] = None
