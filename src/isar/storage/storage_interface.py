from abc import ABCMeta, abstractmethod

from robot_interface.models.mission.mission import Mission
from robot_interface.models.inspection.inspection import Inspection


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(self, inspection: Inspection, mission: Mission) -> str:
        """
        Parameters
        ----------
        mission : Mission
            Mission the inspection is a part of.
        inspection : Inspection
            The inspection object to be stored.

        Returns
        ----------
        String
            Path of the saved inspection

        Raises
        ----------
        StorageException
            An error occurred when storing the inspection.
        """
        pass


class StorageException(Exception):
    pass
