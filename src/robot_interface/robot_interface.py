from abc import ABCMeta, abstractmethod
from typing import Any, Optional, Sequence, Tuple

from robot_interface.models.geometry.joints import Joints
from robot_interface.models.geometry.pose import Pose
from robot_interface.models.inspection.inspection import Inspection, InspectionResult
from robot_interface.models.mission import MissionStatus, Step


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def schedule_step(self, step: Step) -> Tuple[bool, Optional[Any], Optional[Joints]]:
        """Schedules a Mission on the robot.

        The method must adapt the standard mission to the
        specific robots mission planning.

        Parameters
        ----------
        step : Step
            Mission object describing the mission.

        Returns
        -------
        bool
            True if successful of scheduling a mission, false otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def mission_scheduled(self) -> bool:
        """Determines if a mission is scheduled on the robot.

        If a mission is scheduled it may be that another mission
        should not be scheduled.

        Returns
        -------
        bool
            True if a mission is already scheduled, false otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def mission_status(self, mission_id: Any) -> MissionStatus:
        """Retrieves status of the current executing mission for the robot.

        Parameters
        ----------
        mission_id : Any
            Unique identifier for the mission which the status should be checked for

        Returns
        -------
        MissionStatus
            Enum member indicating the current mission status.
        """
        raise NotImplementedError

    @abstractmethod
    def abort_mission(self) -> bool:
        """Aborts the current mission for the robot.

        If another mission is queued, it should not start before a verification
        is sent.

        Returns
        -------
        bool
            True on successful abort of mission, false otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def log_status(
        self, mission_id: Any, mission_status: MissionStatus, current_step: Step
    ) -> None:
        """Logs the status of the executing mission that is being monitored.

        Parameters
        ----------
        mission_id : Any
            Unique identifier for the current executing mission on the robot.
        mission_status : MissionStatus
            Current status of the mission.
        current_step : Step
            The current executing mission step.

        """
        raise NotImplementedError

    @abstractmethod
    def get_inspection_references(
        self, vendor_mission_id: Any, current_step: Step
    ) -> Sequence[Inspection]:
        """Returns inspection references.

        Parameters
        ----------
        vendor_mission_id : Any
            Indicates the vendor id of a mission.
        current_step : Step
            The current executing mission step.

        Returns
        -------
        Sequence[Inspection]
            Returns a sequence of inspections.

        """
        raise NotImplementedError

    @abstractmethod
    def download_inspection_result(
        self, inspection: Inspection
    ) -> Optional[InspectionResult]:
        """Downloads inspection references.

        Parameters
        ----------
        inspection : Inspection
            Inspection references to be downloaded.

        Returns
        -------
        Optional[InspectionResult]
            Returns the downloaded inspection results.

        """
        raise NotImplementedError

    @abstractmethod
    def robot_pose(self) -> Pose:
        """Retrieves the current pose of the robot.

        The pose is given as x, y, z coordinates and quaternion.

        Returns
        -------
        Pose
            Returns the representation of the robot's pose.

        """
        raise NotImplementedError
