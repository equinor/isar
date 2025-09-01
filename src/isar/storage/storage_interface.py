from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

from robot_interface.models.inspection.inspection import InspectionBlob
from robot_interface.models.mission.mission import Mission


class BlobStoragePath(BaseModel):
    storage_account: str
    blob_container: str
    blob_name: str


class LocalStoragePath(BaseModel):
    file_path: Path


TPath = TypeVar("TPath", BlobStoragePath, LocalStoragePath)


class StoragePaths(BaseModel, Generic[TPath]):
    data_path: TPath
    metadata_path: TPath


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(self, inspection: InspectionBlob, mission: Mission) -> StoragePaths:
        """
        Parameters
        ----------
        inspection : InspectionBlob
            The inspection object to be stored.
        mission : Mission
            Mission the inspection is a part of.

        Returns
        ----------
        StoragePaths
            Paths to the data and metadata

        Raises
        ----------
        StorageException
            An error occurred when storing the inspection.
        """
        pass


class StorageException(Exception):
    pass
