from dataclasses import dataclass

from models.inspections.inspection import Inspection


@dataclass
class InspectionResult(Inspection):
    data: bytes
