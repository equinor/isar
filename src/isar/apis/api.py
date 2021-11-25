import logging
from logging import Logger
from typing import Union

import click
import uvicorn
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from injector import inject
from pydantic import AnyHttpUrl

from isar.apis.schedule.drive_to import DriveTo
from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission
from isar.apis.security.authentication import Authenticator
from isar.config import config


class API:
    @inject
    def __init__(
        self,
        authenticator: Authenticator,
        start_mission: StartMission,
        stop_mission: StopMission,
        drive_to: DriveTo,
        host: str = config.get("DEFAULT", "api_host"),
        port: int = config.getint("DEFAULT", "api_port"),
    ) -> None:

        self.authenticator: Authenticator = authenticator
        self.start_mission: StartMission = start_mission
        self.stop_mission: StopMission = stop_mission
        self.drive_to: DriveTo = drive_to
        self.host: str = host
        self.port: int = port

        self.logger: Logger = logging.getLogger("api")

        self.app: FastAPI = self._create_app()

    def get_app(self) -> FastAPI:
        return self.app

    def run_app(self) -> None:
        uvicorn.run(
            self.app,
            port=self.port,
            host=self.host,
            reload=False,
            log_config=None,
        )

    def _create_app(self) -> FastAPI:
        tags_metadata = [
            {
                "name": "Scheduler",
                "description": "Mission functionality",
            }
        ]
        app = FastAPI(
            openapi_tags=tags_metadata,
            on_startup=[self.authenticator.load_config, self._log_startup_message],
            swagger_ui_oauth2_redirect_url="/oauth2-redirect",
            swagger_ui_init_oauth={
                "usePkceWithAuthorizationCodeGrant": True,
                "clientId": self.authenticator.openapi_client_id,
            },
        )

        if self.authenticator.should_authenticate():
            backend_cors_origins: list[Union[str, AnyHttpUrl]] = [
                f"http://{self.host}:{self.port}"
            ]

            app.add_middleware(
                CORSMiddleware,
                allow_origins=[str(origin) for origin in backend_cors_origins],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        app.include_router(router=self._create_scheduler_router())

        return app

    def _create_scheduler_router(self) -> APIRouter:

        router: APIRouter = APIRouter(tags=["Scheduler"])

        authentication_dependency: Security = Security(self.authenticator.get_scheme())

        router.add_api_route(
            "/schedule/start-mission",
            self.start_mission.post,
            methods=["POST"],
            dependencies=[authentication_dependency],
        )

        router.add_api_route(
            "/schedule/stop-mission",
            self.stop_mission.post,
            methods=["POST"],
            dependencies=[authentication_dependency],
        )
        router.add_api_route(
            "/schedule/drive-to",
            self.drive_to.post,
            methods=["POST"],
            dependencies=[authentication_dependency],
        )

        return router

    def _log_startup_message(self) -> None:
        address_format = "%s://%s:%d/docs"
        message = f"Uvicorn running on {address_format} (Press CTRL+C to quit)"
        protocol = "http"
        color_message = (
            "Uvicorn running on "
            + click.style(address_format, bold=True)
            + " (Press CTRL+C to quit)"
        )

        self.logger.info(
            message,
            protocol,
            self.host,
            self.port,
            extra={"color_message": color_message},
        )
