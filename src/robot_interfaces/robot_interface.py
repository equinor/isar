from abc import ABCMeta
from abc import abstractmethod
from typing import Any, Optional, Tuple, Sequence

from models.enums.mission_status import MissionStatus
from models.geometry.joints import Joints
from models.geometry.pose import Pose
from models.inspections.inspection import Inspection
from models.inspections.inspection_result import InspectionResult
from models.planning.step import Step


class RobotInterface(metaclass=ABCMeta):
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

    @abstractmethod
    def get_inspection_references(
        self, vendor_mission_id: Any, current_step: Step
    ) -> Sequence[Inspection]:
        raise NotImplementedError

    @abstractmethod
    def download_inspection_result(
        self, inspection: Inspection
    ) -> Optional[InspectionResult]:
        raise NotImplementedError

    @abstractmethod
    def robot_pose(self) -> Pose:
        """
        Retrieve the current pose of the robot as x, y, z coordinates and quaternion.
        :return: Representation of the robots pose.
        """
        raise NotImplementedError
