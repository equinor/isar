from abc import ABCMeta, abstractmethod

from isar.models.mission_metadata.mission_metadata import MissionMetadata
from robot_interface.models.inspection.inspection import Inspection


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(self, inspection: Inspection, metadata: MissionMetadata):
        """
        Parameters
        ----------
        metadata : MissionMetadata
            Metadata for the mission the inspection is a part of.
        inspection : Inspection
            The inspection object to be stored.

        Raises
        ----------
        StorageException
            An error occurred when storing the inspection.
        """
        pass


class StorageException(Exception):
    pass
