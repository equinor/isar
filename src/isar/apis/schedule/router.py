from fastapi import APIRouter
from injector import Injector

from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission
from isar.apis.security.authentication import Authenticator, Token

from .drive_to import DriveTo


def create_scheduler_router(injector: Injector) -> APIRouter:

    start_mission: StartMission = injector.get(StartMission)
    stop_mission: StopMission = injector.get(StopMission)
    drive_to: DriveTo = injector.get(DriveTo)

    authenticator: Authenticator = Authenticator()

    router: APIRouter = APIRouter(tags=["Scheduler"])

    router.add_api_route(
        "/schedule/start-mission", start_mission.post, methods=["POST"]
    )

    router.add_api_route("/schedule/stop-mission", stop_mission.post, methods=["POST"])
    router.add_api_route("/schedule/drive-to", drive_to.post, methods=["POST"])

    router.add_api_route(
        "/token",
        authenticator.login_for_access_token,
        methods=["POST"],
        response_model=Token,
        include_in_schema=False,
    )
    return router
