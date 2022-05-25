import logging
from dataclasses import asdict
from http import HTTPStatus
from typing import List

from alitra import Frame, Orientation, Pose, Position
from fastapi import Query, Response
from injector import inject

from isar.models.communication.queues.queue_timeout_error import QueueTimeoutError
from isar.models.mission import Mission, Task
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.states_enum import States
from robot_interface.models.mission import DriveToPose


class DriveTo:
    @inject
    def __init__(self, scheduling_utilities: SchedulingUtilities):
        self.logger = logging.getLogger("api")
        self.scheduling_utilities = scheduling_utilities

    def post(
        self,
        response: Response,
        x: float = Query(
            ...,
            alias="x-value",
            description="The target x coordinate",
        ),
        y: float = Query(
            ...,
            alias="y-value",
            description="The target y coordinate",
        ),
        z: float = Query(
            ...,
            alias="z-value",
            description="The target z coordinate",
        ),
        q: List[float] = Query(
            [0, 0, 0, 1],
            alias="quaternion",
            description="The target orientation as a quaternion (x,y,z,w)",
        ),
    ):

        state: States = self.scheduling_utilities.get_state()
        if not state or state != States.Idle:
            response.status_code = HTTPStatus.CONFLICT.value
            return

        robot_frame: Frame = Frame("robot")
        position: Position = Position(x=x, y=y, z=z, frame=robot_frame)
        orientation: Orientation = Orientation(
            x=q[0], y=q[1], z=q[2], w=q[3], frame=robot_frame
        )
        pose: Pose = Pose(position=position, orientation=orientation, frame=robot_frame)

        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission(tasks=[Task(steps=[step])])

        try:
            self.scheduling_utilities.start_mission(mission=mission)
        except QueueTimeoutError:
            response.status_code = HTTPStatus.REQUEST_TIMEOUT.value
