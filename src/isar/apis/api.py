import logging
from http import HTTPStatus
from logging import Logger
from typing import List, Union

import click
import uvicorn
from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from injector import inject
from pydantic import AnyHttpUrl

from isar.apis.models.models import ControlMissionResponse, StartMissionResponse
from isar.apis.schedule.scheduling_controller import SchedulingController
from isar.apis.security.authentication import Authenticator
from isar.config.settings import settings


class API:
    @inject
    def __init__(
        self,
        authenticator: Authenticator,
        scheduling_controller: SchedulingController,
        port: int = settings.API_PORT,
    ) -> None:

        self.authenticator: Authenticator = authenticator
        self.scheduling_controller: SchedulingController = scheduling_controller
        self.host: str = "0.0.0.0"  # Locking uvicorn to use 0.0.0.0
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
            backend_cors_origins: List[Union[str, AnyHttpUrl]] = [
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

        app.include_router(router=self._create_info_router())

        return app

    def _create_scheduler_router(self) -> APIRouter:

        router: APIRouter = APIRouter(tags=["Scheduler"])

        authentication_dependency: Security = Security(self.authenticator.get_scheme())

        router.add_api_route(
            path="/schedule/start-mission/{id}",
            endpoint=self.scheduling_controller.start_mission_by_id,
            methods=["POST"],
            deprecated=True,
            dependencies=[authentication_dependency],
            summary="Start a mission with id='id' from the current mission planner",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Mission succesfully started",
                    "model": StartMissionResponse,
                },
                HTTPStatus.NOT_FOUND.value: {
                    "description": "Not found - Mission not found",
                },
                HTTPStatus.CONFLICT.value: {
                    "description": "Conflict - Invalid command in the current state",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR.value: {
                    "description": "Internal Server Error - Current state of state machine unknown",
                },
            },
        )
        router.add_api_route(
            path="/schedule/start-mission",
            endpoint=self.scheduling_controller.start_mission,
            methods=["POST"],
            dependencies=[authentication_dependency],
            summary="Start the mission provided in JSON format",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Mission succesfully started",
                    "model": StartMissionResponse,
                },
                HTTPStatus.UNPROCESSABLE_ENTITY.value: {
                    "description": "Invalid body - The JSON is incorrect",
                },
                HTTPStatus.CONFLICT.value: {
                    "description": "Conflict - Invalid command in the current state",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR.value: {
                    "description": "Internal Server Error - Current state of state machine unknown",
                },
            },
        )
        router.add_api_route(
            path="/schedule/stop-mission",
            endpoint=self.scheduling_controller.stop_mission,
            methods=["POST"],
            dependencies=[authentication_dependency],
            summary="Stop the current mission",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Mission succesfully stopped",
                    "model": ControlMissionResponse,
                },
                HTTPStatus.CONFLICT.value: {
                    "description": "Conflict - Invalid command in the current state",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR.value: {
                    "description": "Internal Server Error - Current state of state machine unknown",
                },
            },
        )
        router.add_api_route(
            path="/schedule/pause-mission",
            endpoint=self.scheduling_controller.pause_mission,
            methods=["POST"],
            dependencies=[authentication_dependency],
            summary="Pause the current mission",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Mission succesfully paused",
                    "model": ControlMissionResponse,
                },
                HTTPStatus.CONFLICT.value: {
                    "description": "Conflict - Invalid command in the current state",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR.value: {
                    "description": "Internal Server Error - Current state of state machine unknown",
                },
            },
        )
        router.add_api_route(
            path="/schedule/resume-mission",
            endpoint=self.scheduling_controller.resume_mission,
            methods=["POST"],
            dependencies=[authentication_dependency],
            summary="Resume the currently paused mission - if any",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Mission succesfully resumed",
                    "model": ControlMissionResponse,
                },
                HTTPStatus.CONFLICT.value: {
                    "description": "Conflict - Invalid command in the current state",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR.value: {
                    "description": "Internal Server Error - Current state of state machine unknown",
                },
            },
        )
        router.add_api_route(
            path="/schedule/drive-to",
            endpoint=self.scheduling_controller.drive_to,
            methods=["POST"],
            dependencies=[authentication_dependency],
            summary="Drive to the provided pose",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Drive to succesfully started",
                },
                HTTPStatus.CONFLICT.value: {
                    "description": "Conflict - Invalid command in the current state",
                },
                HTTPStatus.INTERNAL_SERVER_ERROR.value: {
                    "description": "Internal Server Error - Current state of state machine unknown",
                },
            },
        )

        return router

    def _create_info_router(self) -> APIRouter:

        router: APIRouter = APIRouter(tags=["Info"])

        authentication_dependency: Security = Security(self.authenticator.get_scheme())

        router.add_api_route(
            path="/info/robot-settings",
            endpoint=self.scheduling_controller.get_info,
            methods=["GET"],
            dependencies=[authentication_dependency],
            summary="Information about the robot-settings",
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
