from abc import ABCMeta, abstractmethod

from robot_interface.models.mission import Mission


class MissionPlannerInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_mission(self, mission_id: int) -> Mission:
        """
        Parameters
        ----------
        mission_id : int

        Returns
        -------
        mission : Mission
        """
        pass


class MissionPlannerError(Exception):
    pass


class MissionNotFoundError(Exception):
    pass
