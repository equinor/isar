import logging
from threading import Event, Thread
from typing import Optional

from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotAlreadyHomeException,
    RobotException,
    RobotInfeasibleMissionException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.robot_interface import RobotInterface


class RobotStartMissionThread(Thread):
    def __init__(
        self,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.robot: RobotInterface = robot
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.mission = mission
        self.error_message: Optional[ErrorMessage] = None
        Thread.__init__(self, name="Robot start mission thread")

    def run(self):
        if self.signal_thread_quitting.wait(0):
            return
        try:
            self.robot.initiate_mission(self.mission)
        except RobotAlreadyHomeException as e:
            self.logger.info(
                "Robot disregarded return to home mission as its already at home. Return home mission will be assumed successful without running."
            )
            self.error_message = ErrorMessage(
                error_reason=e.error_reason,
                error_description=e.error_description,
            )
        except RobotInfeasibleMissionException as e:
            self.logger.error(
                f"Mission is infeasible and cannot be scheduled because: {e.error_description}"
            )
            self.error_message = ErrorMessage(
                error_reason=e.error_reason,
                error_description=e.error_description,
            )
        except RobotException as e:
            self.logger.warning(
                f"Initiating mission failed " f"because: {e.error_description}"
            )
            self.error_message = ErrorMessage(
                error_reason=e.error_reason,
                error_description=e.error_description,
            )
        except Exception as e:
            self.logger.warning(
                f"Initiating mission failed due to unknown exception: {e}"
            )
            self.error_message = ErrorMessage(
                error_reason=ErrorReason.RobotUnknownErrorException,
                error_description=str(e),
            )
