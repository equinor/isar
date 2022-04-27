from abc import ABCMeta, abstractmethod
from typing import Sequence

from alitra import Pose

from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission import InspectionStep, Step, StepStatus


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def initiate_step(self, step: Step) -> None:
        """Send a step to the robot and initiate the execution of the step

        Parameters
        ----------
        step : Step
            The step that should be initiated on the robot.

        Returns
        -------
        None

        Raises
        ------
        RobotException
            If the step is not initiated.

        """
        raise NotImplementedError

    @abstractmethod
    def step_status(self) -> StepStatus:
        """Gets the status of the currently active step on robot.

        Parameters
        ----------
        None

        Returns
        -------
        StepStatus
            Status of the execution of current step.

        Raises:
        ------
        RobotException
            If the step status can't be retrieved.

        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stops the execution of the current step and stops the movement of the robot.

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
    def get_inspections(self, step: InspectionStep) -> Sequence[Inspection]:
        """Return the inspections connected to the given step.

        Parameters
        ----------
        step : Step

        Returns
        -------
        Sequence[InspectionResult]
            List containing all the inspection results connected to the given step.

        Raises
        ------
        RobotException
            If the inspection results can't be retrieved.

        """
        raise NotImplementedError

    @abstractmethod
    def get_pose(self) -> Pose:
        """Return the pose of the robot.

        Returns
        -------
        Pose
            An Alitra pose containing a position, an orientation and a frame.

        Raises
        ------
        RobotException
            If the pose can't be retrieved.

        """
        raise NotImplementedError

    @abstractmethod
    def get_battery(self) -> float:
        """Return the battery level of the robot.

        Returns
        -------
        float
            The battery level of the robot in percentage from 0-100

        Raises
        ------
        RobotException
            If the battery can't be retrieved.

        """
        raise NotImplementedError
