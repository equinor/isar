from pydantic import BaseModel

from robot_interface.models.mission.task import TaskTypes


class TaskResponse(BaseModel):
    id: str
    tag_id: str | None = None
    type: TaskTypes


class StartMissionResponse(BaseModel):
    id: str
    tasks: list[TaskResponse]


class ControlMissionResponse(BaseModel):
    success: bool
    failure_reason: str | None = None


class MissionStartResponse(BaseModel):
    mission_id: str | None = None
    mission_started: bool
    mission_not_started_reason: str | None = None


class LockdownResponse(BaseModel):
    lockdown_started: bool
    failure_reason: str | None = None


class MaintenanceResponse(BaseModel):
    is_maintenance_mode: bool
    failure_reason: str | None = None


class RobotInfoResponse(BaseModel):
    robot_package: str
    isar_id: str
    robot_name: str
    robot_capabilities: list[str]
    robot_map_name: str
    plant_short_name: str
