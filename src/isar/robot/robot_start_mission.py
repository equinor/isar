import logging
from threading import Event, Thread

from isar.config.settings import settings
from isar.models.events import RobotServiceEvents
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
        robot_service_events: RobotServiceEvents,
        robot: RobotInterface,
        signal_thread_quitting: Event,
        mission: Mission,
    ):
        self.logger = logging.getLogger("robot")
        self.robot_service_events: RobotServiceEvents = robot_service_events
        self.robot: RobotInterface = robot
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
                except RobotInfeasibleMissionException as e:
                    self.logger.error(
                        f"Mission is infeasible and cannot be scheduled because: {e.error_description}"
                    )
                    self.robot_service_events.mission_failed.trigger_event(
                        ErrorMessage(
                            error_reason=e.error_reason,
                            error_description=e.error_description,
                        )
                    )

                    break
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

                        self.robot_service_events.mission_failed.trigger_event(
                            ErrorMessage(
                                error_reason=e.error_reason,
                                error_description=e.error_description,
                            )
                        )
                        break

                    continue

                started_mission = True
        except RobotInfeasibleMissionException as e:
            self.robot_service_events.mission_failed.trigger_event(
                ErrorMessage(
                    error_reason=e.error_reason, error_description=e.error_description
                ),
            )

        if started_mission:
            self.robot_service_events.mission_started.trigger_event(True)
