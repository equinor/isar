import logging
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotInfeasibleMissionException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.robot_interface import RobotInterface


class RobotPrepareMissionThread(Thread):
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
        self.cancel_mission_preparation: Event = Event()
        self.error_message: Optional[ErrorMessage] = None

        Thread.__init__(self, name="Robot start mission thread")

    def run(self):
        retries = 0
        mission_prepared = False
        while not mission_prepared:
            if self.signal_thread_quitting.wait(0):
                return
            if self.cancel_mission_preparation.is_set():
                return
            try:
                self.robot.prepare_mission(self.mission)
            except RobotInfeasibleMissionException as e:
                self.logger.error(
                    f"Mission is infeasible and cannot be prepared because: {e.error_description}"
                )
                self.error_message = ErrorMessage(
                    error_reason=e.error_reason,
                    error_description=e.error_description,
                )

                return
            except RobotException as e:
                retries += 1
                self.logger.warning(
                    f"Initiating failed #: {str(retries)} "
                    f"because: {e.error_description}"
                )

                if retries >= settings.INITIATE_FAILURE_COUNTER_LIMIT:
                    self.logger.error(
                        f"Mission will be cancelled after failing to initiate "
                        f"{settings.INITIATE_FAILURE_COUNTER_LIMIT} times because: "
                        f"{e.error_description}"
                    )

                    self.error_message = ErrorMessage(
                        error_reason=e.error_reason,
                        error_description=e.error_description,
                    )
                    return

                continue

            mission_prepared = True
