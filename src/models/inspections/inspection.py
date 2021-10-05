from dataclasses import dataclass
from typing import Any

from models.metadata.inspection_metadata import InspectionMetadata


@dataclass
class Inspection:
    id: Any
    metadata: InspectionMetadata
