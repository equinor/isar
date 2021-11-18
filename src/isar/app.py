from fastapi import FastAPI

from injector import Injector
from fastapi.middleware.cors import CORSMiddleware
from isar.apis.schedule.router import create_scheduler_router
from isar.apis.security.authentication import Authenticator


def create_app(injector: Injector, authentication_enabled: bool = False):

    tags_metadata = [
        {
            "name": "Scheduler",
            "description": "Mission functionality",
        }
    ]

    authenticator = Authenticator()

    app = FastAPI(
        openapi_tags=tags_metadata,
        on_startup=[authenticator.load_config],
        swagger_ui_oauth2_redirect_url="/oauth2-redirect",
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": authenticator.openapi_client_id,
        },
    )

    if authentication_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                str(origin) for origin in authenticator.backend_cors_origins
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(router=create_scheduler_router(injector=injector))
    return app
