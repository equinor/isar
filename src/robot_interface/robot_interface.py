from abc import ABCMeta, abstractmethod
from typing import Sequence

from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission import InspectionTask, Task, TaskStatus


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def initiate_task(self, task: Task) -> None:
        """Send a task to the robot and start the execution of the task

        Parameters
        ----------
        task : Task
            The task that should be initiated on the robot.

        Returns
        -------
        None

        Raises
        ------
        RobotException
            If the task is not initiated.

        """
        raise NotImplementedError

    @abstractmethod
    def task_status(self) -> TaskStatus:
        """Gets the status of the currently active task on robot.

        Parameters
        ----------
        None

        Returns
        -------
        TaskStatus
            Status of the execution of current task.

        Raises:
        ------
        RobotException
            If the task status can't be retrived.

        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stops the execution of the current task and stops the movement of the robot.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        RobotException
            If the robot is not stopped.

        """
        raise NotImplementedError

    @abstractmethod
    def get_inspections(self, task: InspectionTask) -> Sequence[Inspection]:
        """Return the inspecitons connected to the given task.

        Parameters
        ----------
        task : Task

        Returns
        -------
        Sequence[InpsectionResult]
            List containing all the inspection results connected to the given task.

        Raises
        ------
        RobotException
            If the inspection results can't be retrived.

        """
        raise NotImplementedError
