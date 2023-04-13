import logging
import os
from http import HTTPStatus
from logging import Logger
from typing import List, Union

import click
import uvicorn
from fastapi import FastAPI, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from injector import inject
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.span import SpanKind
from opencensus.trace.tracer import Tracer
from pydantic import AnyHttpUrl

from isar.apis.models.models import ControlMissionResponse, StartMissionResponse
from isar.apis.schedule.scheduling_controller import SchedulingController
from isar.apis.security.authentication import Authenticator
from isar.config.configuration_error import ConfigurationError
from isar.config.keyvault.keyvault_error import KeyvaultError
from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings

HTTP_URL = COMMON_ATTRIBUTES["HTTP_URL"]
HTTP_STATUS_CODE = COMMON_ATTRIBUTES["HTTP_STATUS_CODE"]


class API:
    @inject
    def __init__(
        self,
        authenticator: Authenticator,
        scheduling_controller: SchedulingController,
        keyvault_client: Keyvault,
        port: int = settings.API_PORT,
        azure_ai_logging_enabled: bool = settings.LOG_HANDLER_APPLICATION_INSIGHTS_ENABLED,
    ) -> None:
        self.authenticator: Authenticator = authenticator
        self.scheduling_controller: SchedulingController = scheduling_controller
        self.keyvault_client: Keyvault = keyvault_client
        self.host: str = "0.0.0.0"  # Locking uvicorn to use 0.0.0.0
        self.port: int = port
        self.azure_ai_logging_enabled: bool = azure_ai_logging_enabled

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
                "clientId": settings.AZURE_CLIENT_ID,
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

        if self.azure_ai_logging_enabled:
            self._add_request_logging_middleware(app)

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
        router.add_api_route(
            path="/schedule/start-localization-mission",
            endpoint=self.scheduling_controller.start_localization_mission,
            methods=["POST"],
            dependencies=[authentication_dependency],
            summary="Localize at the provided pose",
            responses={
                HTTPStatus.OK.value: {
                    "description": "Localization succesfully started",
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

    def _add_request_logging_middleware(self, app: FastAPI) -> None:
        connection_string: str
        try:
            connection_string = self.keyvault_client.get_secret(
                "application-insights-connection-string"
            ).value
        except KeyvaultError:
            message: str = (
                "Missing connection string for Application Insights in key vault. "
            )
            self.logger.critical(message)
            raise ConfigurationError(message)

        @app.middleware("http")
        async def middlewareOpencensus(request: Request, call_next):
            tracer = Tracer(
                exporter=AzureExporter(connection_string=connection_string),
                sampler=ProbabilitySampler(1.0),
            )
            with tracer.span("main") as span:
                span.span_kind = SpanKind.SERVER

                response = await call_next(request)

                tracer.add_attribute_to_current_span(
                    attribute_key=HTTP_STATUS_CODE, attribute_value=response.status_code
                )
                tracer.add_attribute_to_current_span(
                    attribute_key=HTTP_URL, attribute_value=str(request.url)
                )

            return response
