from typing import List

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.storage.storage_interface import StorageException, StorageInterface
from robot_interface.models.inspection.inspection import Inspection


class StorageMock(StorageInterface):
    will_fail: bool = False

    def __init__(self) -> None:
        self.stored_inspections: List[Inspection] = []

    def store(self, inspection: Inspection, metadata: MissionMetadata):
        if self.will_fail:
            raise StorageException("Mock failed on purpose")
        self.stored_inspections.append(inspection)

    def blob_exists(self, inspection: Inspection) -> bool:
        return inspection in self.stored_inspections
