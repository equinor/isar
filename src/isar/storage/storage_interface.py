from abc import ABCMeta, abstractmethod
from typing import Union

from robot_interface.models.inspection.inspection import InspectionBlob
from robot_interface.models.mission.mission import Mission


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(self, inspection: InspectionBlob, mission: Mission) -> Union[str, dict]:
        """
        Parameters
        ----------
        mission : Mission
            Mission the inspection is a part of.
        inspection : InspectionBlob
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
