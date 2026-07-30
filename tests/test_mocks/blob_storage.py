from isar.storage.storage_interface import (
    BlobStoragePath,
    StorageException,
    StorageInterface,
    StoragePaths,
)
from robot_interface.models.inspection.inspection import Inspection, InspectionBlob
from robot_interface.models.mission.mission import Mission


class StorageFake(StorageInterface):
    failure_count: int = 0

    def __init__(self) -> None:
        self.stored_inspections: list[Inspection] = []

    def store(
        self, inspection: InspectionBlob, mission: Mission
    ) -> StoragePaths[BlobStoragePath]:
        if self.failure_count > 1:
            self.failure_count -= 1
            raise StorageException("Fake failed on purpose")
        self.stored_inspections.append(inspection)
        path = BlobStoragePath(
            storage_account="acct", blob_container="cont", blob_name="blob"
        )
        return StoragePaths(data_path=path, metadata_path=path)

    def blob_exists(self, inspection: Inspection) -> bool:
        return inspection in self.stored_inspections


class StorageEmptyBlobPathsFake(StorageInterface):

    def __init__(self) -> None:
        self.stored: list[Inspection] = []
        self.fail: bool = False

    def store(
        self, inspection: InspectionBlob, mission: Mission
    ) -> StoragePaths[BlobStoragePath]:
        if self.fail:
            raise StorageException("fail on purpose")
        self.stored.append(inspection)
        empty = BlobStoragePath(storage_account="", blob_container="", blob_name="")
        return StoragePaths(data_path=empty, metadata_path=empty)
