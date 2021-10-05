import abc
from abc import abstractmethod
from typing import Any, Optional, Sequence

from models.inspections.inspection import Inspection
from models.inspections.inspection_result import InspectionResult
from models.planning.step import Step


class RobotStorageInterface(metaclass=abc.ABCMeta):
    @abstractmethod
    def get_inspection_references(
        self, vendor_mission_id: Any, current_step: Step
    ) -> Sequence[Inspection]:
        pass

    @abstractmethod
    def download_inspection_result(
        self, inspection: Inspection
    ) -> Optional[InspectionResult]:
        pass
