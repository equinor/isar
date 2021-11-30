from abc import ABCMeta, abstractmethod
from typing import Optional, Sequence, Tuple
from uuid import UUID

from robot_interface.models.geometry.pose import Pose
from robot_interface.models.inspection.inspection import Inspection, InspectionResult
from robot_interface.models.mission import Task, TaskStatus


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def schedule_task(self, task: Task) -> bool:
        """Schedules a Task on the robot.

        The method must adapt the standard mission to the
        specific robots mission planning.

        Parameters
        ----------
        task : Task
            Task object describing the mission task.

        Returns
        -------
        bool
            True if successful of scheduling a task, false otherwise.
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
    def task_status(self, task_id: Optional[UUID]) -> TaskStatus:
        """Retrieves status of the task with the given id. If task id is not specified,
        the status of the current executing mission task is returned.

        Parameters
        ----------
        task_id : UUID
            Unique identifier for the mission task which the status should be checked for.

        Returns
        -------
        TaskStatus
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
    def log_status(self, task_status: TaskStatus, current_task: Task) -> None:
        """Logs the status of the executing task that is being monitored.

        Parameters
        ----------
        task_status : TaskStatus
            Status of the mission task.
        current_task : Task
            The current executing mission task.

        """
        raise NotImplementedError

    @abstractmethod
    def get_inspection_references(self, current_task: Task) -> Sequence[Inspection]:
        """Returns inspection references of the inspections in the given task.

        Parameters
        ----------
        current_task : Task
            The current executing mission task.

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
