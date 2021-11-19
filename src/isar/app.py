from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from injector import Injector
from pydantic import AnyHttpUrl

from isar.apis.schedule.router import create_scheduler_router
from isar.apis.security.authentication import Authenticator
from isar.config import config


def create_app(
    injector: Injector,
    host: str = config.get("fastapi", "run_host"),
    port: int = config.getint("fastapi", "run_port"),
):

    tags_metadata = [
        {
            "name": "Scheduler",
            "description": "Mission functionality",
        }
    ]

    authenticator = injector.get(Authenticator)

    app = FastAPI(
        openapi_tags=tags_metadata,
        on_startup=[authenticator.load_config],
        swagger_ui_oauth2_redirect_url="/oauth2-redirect",
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": authenticator.openapi_client_id,
        },
    )

    if authenticator.should_authenticate():
        backend_cors_origins: list[Union[str, AnyHttpUrl]] = [f"http://{host}:{port}"]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in backend_cors_origins],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(router=create_scheduler_router(injector=injector))

    return app
