import logging
from dataclasses import asdict
from typing import List

from alitra import Frame, Orientation, Pose, Position
from fastapi import Query
from injector import inject
from starlette.responses import JSONResponse

from isar.models.mission import Mission, Task
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from robot_interface.models.mission import DriveToPose


class DriveTo:
    @inject
    def __init__(self, scheduling_utilities: SchedulingUtilities):
        self.logger = logging.getLogger("api")
        self.scheduling_utilities = scheduling_utilities

    def post(
        self,
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

        ready, response = self.scheduling_utilities.ready_to_start_mission()
        if not ready:
            message, status_code = response
            return JSONResponse(content=asdict(message), status_code=status_code)
        robot_frame: Frame = Frame("robot")
        position: Position = Position(x=x, y=y, z=z, frame=robot_frame)
        orientation: Orientation = Orientation(
            x=q[0], y=q[1], z=q[2], w=q[3], frame=robot_frame
        )
        pose: Pose = Pose(position=position, orientation=orientation, frame=robot_frame)

        step: DriveToPose = DriveToPose(pose=pose)
        mission: Mission = Mission(tasks=[Task(steps=[step])])

        response = self.scheduling_utilities.start_mission(mission=mission)
        self.logger.info(response)
        message, status_code = response

        return JSONResponse(content=asdict(message), status_code=status_code)
