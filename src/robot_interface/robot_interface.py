from abc import ABCMeta, abstractmethod
from queue import Queue
from threading import Thread
from typing import List, Sequence

from robot_interface.models.initialize import InitializeParams
from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, RobotStatus, StepStatus
from robot_interface.models.mission.step import InspectionStep, Step


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def initiate_mission(self, mission: Mission) -> None:
        """Send a mission to the robot and initiate execution of the mission

        This function should be used in combination with the mission_status function
        if the robot is designed to run full missions and not in a stepwise
        configuration.

        Parameters
        ----------
        mission: Mission

        Returns
        -------
        None

        Raises
        ------
        RobotInfeasibleMissionException
            If the mission input is infeasible and the mission fails to be scheduled in
            a way that means attempting to schedule again is not necessary
        RobotException
            Will catch all RobotExceptions not previously listed and retry scheduling of
            the mission until the number of allowed retries is exceeded
        NotImplementedError
            If the robot is designed for stepwise mission execution

        """
        raise NotImplementedError

    def mission_status(self) -> MissionStatus:
        """Gets the status of the currently active mission on the robot

        This function should be used in combination with the initiate_mission function
        if the robot is designed to run full missions and not in a stepwise
        configuration.

        Returns
        -------
        MissionStatus
            Status of the executing mission on the robot.

        Raises
        ------
        RobotMissionStatusException
            If the mission status could not be collected this will lead to the mission
            being marked as failed
        RobotException
            An uncaught RobotException in the robot package while retrieving the status
            will cause the mission to be marked as failed
        NotImplementedError
            If the robot is designed for stepwise mission execution

        """

    @abstractmethod
    def initiate_step(self, step: Step) -> None:
        """Send a step to the robot and initiate the execution of the step

        This function should be used in combination with the step_status function
        if the robot is designed to run stepwise missions and not in a full mission
        configuration.

        Parameters
        ----------
        step : Step
            The step that should be initiated on the robot.

        Returns
        -------
        None

        Raises
        ------
        RobotInfeasibleStepException
            If the step input is infeasible and the step fails to be scheduled in
            a way that means attempting to schedule again is not necessary
        RobotException
            Will catch all RobotExceptions not previously listed and retry scheduling
            of the step until the number of allowed retries is exceeded before the step
            will be marked as failed and the mission cancelled
        NotImplementedError
            If the robot is designed for full mission execution.

        """
        raise NotImplementedError

    @abstractmethod
    def step_status(self) -> StepStatus:
        """Gets the status of the currently active step on robot.

        This function should be used in combination with the initiate_step function
        if the robot is designed to run stepwise missions and not in a full mission
        configuration.

        Returns
        -------
        StepStatus
            Status of the execution of current step.

        Raises
        ------
        RobotException
            If the step status could not be retrieved.
        NotImplementedError
            If the robot is designed for full mission execution.

        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stops the execution of the current step and stops the movement of the robot.

        Returns
        -------
        None

        Raises
        ------
        RobotActionException
            If the robot fails to perform the requested action to stop mission execution
            the action to stop will be attempted again until a certain number of retries
        RobotException
            Will catch other RobotExceptions and retry to stop the mission

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
            List containing all the inspection results connected to the given step

        Raises
        ------
        RobotRetrieveInspectionException
            If the robot package is unable to retrieve the inspections for the relevant
            mission or step an error message is logged and the state machine continues
        RobotException
            Catches other RobotExceptions that lead to the same result as a
            RobotRetrieveInspectionException

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
        RobotInitializeException
            If the robot package is unable to initialize the robot correctly the mission
            will be cancelled
        RobotException
            Catches other RobotExceptions that might have occurred during initialization
            where the result is that the mission is cancelled

        """
        raise NotImplementedError

    @abstractmethod
    def get_telemetry_publishers(
        self, queue: Queue, isar_id: str, robot_name: str
    ) -> List[Thread]:
        """
        Set up telemetry publisher threads to publish regular updates for pose, battery
        level etc. from the robot to the MQTT broker. The publishers on the robot side
        will use the queue to pass messages to the MQTT Client on the ISAR side.

        The isar_id is passed to the robot to ensure the messages are published to the
        correct topics.

        Note that this functionality will only be utilized if MQTT is enabled in the
        settings.

        Returns
        -------
        List[Thread]
            List containing all threads that will be started to publish telemetry.
        """
        raise NotImplementedError

    @abstractmethod
    def robot_status(self) -> RobotStatus:
        """
        Method which returns an enum indicating if the robot package is able to reach
        the interface which is used to communicate with the robot. This is further used
        by ISAR to indicate whether the ISAR instance is fully functional and may be
        used by other systems.

        Returns
        -------
        RobotStatus
            Enum indicating if the robot may be reached by the isar-robot package.

        Raises
        -------
        RobotCommunicationException
            Raised if the robot package is unable to communicate with the robot API
        RobotAPIException
            Raised if the robot package is able to communicate with the API but an error
            occurred while interpreting the response
        RobotException
            Catches other RobotExceptions that may have occurred while retrieving the
            robot status
            At this point ISAR will attempt to request the robot status again
        """
        raise NotImplementedError
