import abc
from abc import abstractmethod
from typing import Any, Optional, Tuple

from models.enums.mission_status import MissionStatus
from models.geometry.joints import Joints
from models.planning.step import Step


class RobotSchedulerInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "schedule_mission")
            and callable(subclass.schedule_step)
            and hasattr(subclass, "mission_scheduled")
            and callable(subclass.mission_scheduled)
            and hasattr(subclass, "mission_status")
            and callable(subclass.mission_status)
            and hasattr(subclass, "abort_mission")
            and callable(subclass.abort_mission)
            and hasattr(subclass, "log_status")
            and callable(subclass.log_status)
            or NotImplemented
        )

    @abstractmethod
    def schedule_step(self, step: Step) -> Tuple[bool, Optional[Any], Optional[Joints]]:
        """
        Schedule a Mission on the robot. The method must adapt the standard mission to the
        specific robots mission planning.
        :param step: Mission object describing the mission
        :return: Boolean indicating success of scheduling of mission
        """
        raise NotImplementedError

    @abstractmethod
    def mission_scheduled(self) -> bool:
        """
        Determine if a mission is scheduled on the robot. If a mission is scheduled it may be that another mission
        should not be scheduled.
        :return: Boolean indicating whether a mission is already scheduled
        """
        raise NotImplementedError

    @abstractmethod
    def mission_status(self, mission_id: Any) -> MissionStatus:
        """
        Retrieves status of the current executing mission for the robot.
        :param mission_id: Unique identifier for the mission which the status should be checked for
        :return: MissionStatus enum member indicating current mission status
        """
        raise NotImplementedError

    @abstractmethod
    def abort_mission(self) -> bool:
        """
        Abort the current mission for the robot. If another mission is queued, it should not start before a verification
        is sent.
        :return: Boolean indicating successful abort of mission
        """
        raise NotImplementedError

    @abstractmethod
    def log_status(
        self, mission_id: Any, mission_status: MissionStatus, current_step: Step
    ):
        """
        Function which logs the status of the executing mission that is being monitored.
        :param mission_id: Unique identifier for the current executing mission on the robot.
        :param mission_status: Current status of the mission.
        :param current_step: The current executing mission step.
        :return:
        """
        raise NotImplementedError
