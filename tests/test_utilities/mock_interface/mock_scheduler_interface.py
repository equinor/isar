import logging
from logging import Logger
from typing import Any, Optional, Tuple

from models.enums.mission_status import MissionStatus
from models.geometry.joints import Joints
from models.planning.step import Step
from robot_interfaces.robot_scheduler_interface import RobotSchedulerInterface


class MockScheduler(RobotSchedulerInterface):
    def __init__(
        self,
        schedule_step: Tuple[bool, Optional[Any], Optional[Joints]] = (True, 1, None),
        mission_scheduled: bool = False,
        mission_status: MissionStatus = MissionStatus.InProgress,
        abort_mission: bool = True,
    ):
        self.logger: Logger = logging.getLogger()
        self.schedule_step_return_value: Tuple[
            bool, Optional[Any], Optional[Joints]
        ] = schedule_step
        self.mission_scheduled_return_value: bool = mission_scheduled
        self.mission_status_return_value: MissionStatus = mission_status
        self.abort_mission_return_value: bool = abort_mission

    def schedule_step(self, step: Step) -> Tuple[bool, Optional[Any], Optional[Joints]]:
        self.logger.info("Mock for schedule_step in scheduler was called")
        return self.schedule_step_return_value

    def mission_scheduled(self) -> bool:
        self.logger.info("Mock for mission_scheduled in scheduler was called")

        return self.mission_scheduled_return_value

    def mission_status(self, mission_id: Any) -> MissionStatus:
        self.logger.info("Mock for mission_status in scheduler was called")
        return self.mission_status_return_value

    def abort_mission(self) -> bool:
        self.logger.info("Mock for abort_mission in scheduler was called")
        return self.abort_mission_return_value

    def log_status(
        self, mission_id: Any, mission_status: MissionStatus, current_step: Step
    ):
        self.logger.info("Mock for log_status in scheduler was called")
