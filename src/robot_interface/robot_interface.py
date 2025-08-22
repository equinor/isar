from abc import ABCMeta, abstractmethod
from queue import Queue
from threading import Thread
from typing import Callable, List, Optional

from robot_interface.models.inspection.inspection import Inspection
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import RobotStatus, TaskStatus
from robot_interface.models.mission.task import InspectionTask
from robot_interface.models.robots.media import MediaConfig


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def initiate_mission(self, mission: Mission) -> None:
        """Send a mission to the robot and initiate execution of the mission

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

        """
        raise NotImplementedError

    @abstractmethod
    def task_status(self, task_id: str) -> TaskStatus:
        """Gets the status of the currently active task on robot.

        Returns
        -------
        TaskStatus
            Status of the execution of current task.

        Raises
        ------
        RobotCommunicationTimeoutException or RobotCommunicationException
            If the robot package is unable to communicate with the robot API the fetching
            of task status will be attempted again until a certain number of retries
        RobotException
            If the task status could not be retrieved.

        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stops the execution of the current task and corresponding mission.

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
    def pause(self) -> None:
        """Pauses the execution of the current task and stops the movement of the robot.

        Returns
        -------
        None

        Raises
        ------
        RobotActionException
            If the robot fails to perform the requested action to pause mission execution
            the action to pause will be attempted again until a certain number of retries
        RobotException
            Will catch other RobotExceptions and retry to pause the mission

        """
        raise NotImplementedError

    @abstractmethod
    def resume(self) -> None:
        """Resumes the execution of the current task and continues the rest of the mission.

        Returns
        -------
        None

        Raises
        ------
        RobotActionException
            If the robot fails to perform the requested action to resume mission execution
            the action to resume will be attempted again until a certain number of retries
        RobotException
            Will catch other RobotExceptions and retry to resume the mission

        """
        raise NotImplementedError

    @abstractmethod
    def get_inspection(self, task: InspectionTask) -> Inspection:
        """Return the inspection connected to the given task.

        Parameters
        ----------
        task : InspectionTask

        Returns
        -------
        Inspection
            The inspection connected to the given task.
            get_inspection has responsibility to assign the inspection_id of the task
            to the inspection that it returns.

        Raises
        ------
        RobotRetrieveInspectionException
            If the robot package is unable to retrieve the inspections for the relevant
            mission or task an error message is logged and the state machine continues
        RobotException
            Catches other RobotExceptions that lead to the same result as a
            RobotRetrieveInspectionException

        """
        raise NotImplementedError

    @abstractmethod
    def register_inspection_callback(
        self, callback_function: Callable[[Inspection, Mission], None]
    ) -> None:
        """Register a function which should be run when inspection data is received
        asynchronously. This function should expect to receive an Inspection from.

        Parameters
        ----------
        callback_function : Callable[[Inspection, Mission], None]

        Returns
        -------
        None

        """
        raise NotImplementedError

    @abstractmethod
    def initialize(self) -> None:
        """Initializes the robot. The initialization needed is robot dependent and the
        function can be a simple return statement if no initialization is needed for the
        robot.

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
    def generate_media_config(self) -> Optional[MediaConfig]:
        """
        Generate a JSON containing the url and token needed to establish a media stream
        connection to a robot.

        Returns
        -------
        MediaConfig
            An object containing the connection information for a media stream connection

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
        Method which returns an enum indicating the status of the robot.

        Returns
        -------
        RobotStatus
            Enum indicating if the robot may be reached by the isar-robot package.

        Raises
        -------
        RobotCommunicationException
            Raised if the robot package is unable to communicate with the robot API.
            The fetching of robot status will be attempted again until success
        RobotAPIException
            Raised if the robot package is able to communicate with the API but an error
            occurred while interpreting the response. The fetching of robot status will
            be attempted again until success
        RobotException
            Catches other RobotExceptions that may have occurred while retrieving the
            robot status. The fetching of robot status will be attempted again until
            success

        """
        raise NotImplementedError

    @abstractmethod
    def get_battery_level(self) -> float:
        """
        Method which returns the percent charge remaining in the robot battery.

        Returns
        -------
        float
            The battery percentage on the robot

        Raises
        -------
        RobotCommunicationException
            Raised if the robot package is unable to communicate with the robot API.
            The fetching of robot battery level will be attempted again until success
        RobotAPIException
            Raised if the robot package is able to communicate with the API but an error
            occurred while interpreting the response. The fetching of robot battery level
            will be attempted again until success
        RobotException
            Catches other RobotExceptions that may have occurred while retrieving the
            robot battery level. The fetching of robot battery level will
            be attempted again until success

        """
        raise NotImplementedError
