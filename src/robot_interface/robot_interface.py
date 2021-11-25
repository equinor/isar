from abc import ABCMeta, abstractmethod
from typing import Optional, Sequence
from uuid import UUID

from robot_interface.models.inspection.inspection import InspectionResult
from robot_interface.models.sensor.status import SensorStatus
from robot_interface.models.step.step import InspectionStep, Step
from robot_interface.models.step.status import StepStatus
from robot_interface.models.sensor.sensor import Sensor


class RobotInterface(metaclass=ABCMeta):
    """Interface to communicate with robots."""

    @abstractmethod
    def stop(self) -> None:
        """Stops the execution of the current scheduled step
        and stops the movements of the robot.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def dock(self) -> None:
        """Orders to move back to the docking station and start
        the docking procedure.

        Parameters
        ----------
        None

        Returns
        -------
        None

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def schedule_step(self, step: Step) -> None:
        """Schedules a step on the robot.

        The method must adapt the standard step to the
        specific robots mission planning.

        Parameters
        ----------
        step : Step
            Step object that describes the intended task for the
            robot to perform.

        Returns
        -------
        None

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def step_status(self, step: Optional[Step] = None) -> StepStatus:
        """Function that returns the status of the progress for
        a given step.

        Parameters
        ----------
        step : Optional[Step]
            Step object that indicate which step to check status for.
            None indicates current step.

        Returns
        -------
        StepStatus
            The status of the desired step

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def get_inspection_step_results(
        self, inspection_step: InspectionStep
    ) -> Sequence[InspectionResult]:
        """Get the inspection result data from a scheduled inspection
        step.

        Parameters
        ----------
        inspection_step : InspectionStep
            The Step that we want to get the inpection results for.

        Returns
        -------
        Sequence[InspectionResult]
            A list containing all the insepction results connected to
            a the provided step.

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def get_sensor_recordings(self, sensor: Sensor) -> Sequence[InspectionResult]:
        """Get the recorded data from the given sensor.

        Parameters
        ----------
        sensor : Sensor
            The Sensor we want the recorded data from.

        Returns
        -------
        Sequence[InspectionResult]
            A list containing all the insepction results connected to
            the given sensor.

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def start_sensor_recording(
        self, id: UUID, sensor: Sensor, time: Optional[float] = None
    ) -> None:
        """Starts a recording of the given sensors output
        (video, audio etc). Does nothing if the sensor is already
        recording

        The recording lasts until a stop signal is given or the
        desired time length is achived.

        Parameters
        ----------
        sensor : Sensor
            Sensor object that describes which sensor that should
            be started.

        time : Optional[float]
            The desired time length of the recording. None
            indicates that the sensor should record until
            a stop signal is given.

        Returns
        -------
        None

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def stop_sensor_recording(self, sensor: Sensor) -> None:
        """Stops recording for the given sensor. Does nothing
        if the sensor is not recording.

        Parameters
        ----------
        sensor : Sensor
            Sensor object that indicates which sensor to stop.

        Returns
        -------
        None

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError

    @abstractmethod
    def sensor_status(self, sensor: Sensor) -> SensorStatus:
        """Gives the current status of the given sensor.

        Parameters
        ----------
        sensor : Sensor
            Sensor object that indicates which sensor to get status
            for.

        Returns
        -------
        SensorStatus
            The status of the given sensor

        Raises
        ------
        RobotException if function fails
        """
        raise NotImplementedError
