from fastapi import FastAPI
from injector import Injector

from isar.apis.schedule.router import create_scheduler_router


def create_app(injector: Injector):

    tags_metadata = [
        {
            "name": "Scheduler",
            "description": "Mission functionality",
        }
    ]

    app = FastAPI(openapi_tags=tags_metadata)

    app.include_router(router=create_scheduler_router(injector=injector))

    return app
