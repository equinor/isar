from abc import ABCMeta, abstractmethod


class StorageInterface(metaclass=ABCMeta):
    @abstractmethod
    def store(self, data: bytes, path: str):
        """
        Parameters
        ----------
        data : bytes
            The data to be stored.
        path : str
            Path to destination, relative from root folder in storage.
        """
        pass
