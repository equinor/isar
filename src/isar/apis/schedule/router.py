from fastapi import APIRouter
from injector import Injector

from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission

from .drive_to import DriveTo


def create_scheduler_router(injector: Injector) -> APIRouter:

    start_mission: StartMission = injector.get(StartMission)
    stop_mission: StopMission = injector.get(StopMission)
    drive_to: DriveTo = injector.get(DriveTo)

    router: APIRouter = APIRouter(tags=["Scheduler"])

    router.add_api_route(
        "/schedule/start-mission", start_mission.post, methods=["POST"]
    )

    router.add_api_route("/schedule/stop-mission", stop_mission.post, methods=["POST"])
    router.add_api_route("/schedule/drive-to", drive_to.post, methods=["POST"])

    return router
