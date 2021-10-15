from abc import ABCMeta, abstractmethod
from pathlib import Path


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(self, data: bytes, path: Path) -> bool:
        """
        Parameters
        ----------
        data : bytes
            The data to be stored.
        path : pathlib.Path
            Path to destination, relative from root folder in storage.
        """
        pass
