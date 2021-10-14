from abc import ABCMeta, abstractmethod

from isar.models.mission import Mission


class MissionPlannerInterface(metaclass=ABCMeta):
    @abstractmethod
    def get_mission(self, mission_id: int) -> Mission:
        pass
