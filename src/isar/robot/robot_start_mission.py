import logging
from threading import Event, Thread
from typing import Optional

from isar.config.settings import settings
from isar.models.communication.queues.queue_utils import trigger_event
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.threaded_request import ThreadedRequest
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    RobotException,
    RobotInfeasibleMissionException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.robot_interface import RobotInterface


class RobotStartMissionThread(Thread):

    def __init__(
        self,
        queues: Queues,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.queues: Queues = queues
        self.robot: RobotInterface = robot
        self.start_mission_thread: Optional[ThreadedRequest] = None
        self.signal_thread_quitting: Event = signal_thread_quitting
        self.mission = mission
        Thread.__init__(self, name="Robot start mission thread")

    def run(self):
        retries = 0
        started_mission = False
        try:
            while not started_mission:
                if self.signal_thread_quitting.wait(0):
                    return
                try:
                    self.robot.initiate_mission(self.mission)
                except RobotException as e:
                    retries += 1
                    self.logger.warning(
                        f"Initiating failed #: {str(retries)} "
                        f"because: {e.error_description}"
                    )

                    if retries >= settings.INITIATE_FAILURE_COUNTER_LIMIT:
                        error_description = (
                            f"Mission will be cancelled after failing to initiate "
                            f"{settings.INITIATE_FAILURE_COUNTER_LIMIT} times because: "
                            f"{e.error_description}"
                        )

                        trigger_event(
                            self.queues.robot_mission_failed,
                            ErrorMessage(
                                error_reason=e.error_reason,
                                error_description=error_description,
                            ),
                        )
                started_mission = True
        except RobotInfeasibleMissionException as e:
            trigger_event(
                self.queues.robot_mission_failed,
                ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                ),
            )
        trigger_event(self.queues.robot_mission_started)
