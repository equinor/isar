from abc import ABCMeta, abstractmethod
from queue import Queue
from threading import Thread
from typing import List, Sequence

from robot_interface.models.initialize import InitializeParams
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
    def initialize(self, params: InitializeParams) -> None:
        """Initializes the robot. The initialization needed is robot dependent and the
        function can be a simple return statement if no initialization is needed for the
        robot.

        Parameters
        ----------
        params: InitializeParams

        Returns
        -------
        None

        Raises
        ------
        RobotException
            If the initialization failed

        """
        raise NotImplementedError

    @abstractmethod
    def get_telemetry_publishers(self, queue: Queue, robot_id: str) -> List[Thread]:
        """
        Set up telemetry publisher threads to publish regular updates for pose, battery
        level etc. from the robot to the MQTT broker. The publishers on the robot side
        will use the queue to pass messages to the MQTT Client on the ISAR side.

        The robot_id is passed to the robot to ensure the messages are published to the
        correct topics.

        Note that this functionality will only be utilized if MQTT is enabled in the
        settings.

        Returns
        -------
        List[Thread]
            List containing all threads that will be started to publish telemetry.

        """
        raise NotImplementedError
