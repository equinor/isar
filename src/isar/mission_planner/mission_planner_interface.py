from abc import ABCMeta, abstractmethod

from robot_interface.models.mission.mission import Mission


class MissionPlannerInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_mission(self, mission_id: str) -> Mission:
        """
        Parameters
        ----------
        mission_id : str

        Returns
        -------
        mission : Mission
        """
        pass


class MissionPlannerError(Exception):
    pass


class MissionNotFoundError(Exception):
    pass
