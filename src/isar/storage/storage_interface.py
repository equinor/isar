from abc import ABCMeta, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from robot_interface.models.inspection.inspection import InspectionBlob, InspectionValue
from robot_interface.models.mission.mission import Mission


class BlobStoragePath(BaseModel):
    storage_account: str
    blob_container: str
    blob_name: str


class LocalStoragePath(BaseModel):
    file_path: Path


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(
        self, inspection: InspectionBlob | InspectionValue, mission: Mission
    ) -> BlobStoragePath | LocalStoragePath:
        """
        Parameters
        ----------
        inspection : InspectionBlob | InspectionValue
            The inspection object to be stored.
        mission : Mission
            Mission the inspection is a part of.

        Returns
        ----------
        BlobStoragePath or LocalStoragePath
            Path to the inspection data

        Raises
        ----------
        StorageException
            An error occurred when storing the inspection.
        """


class StorageException(Exception):
    pass
