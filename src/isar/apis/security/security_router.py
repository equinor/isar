from fastapi import APIRouter
from injector import Injector

from isar.apis.security.authentication import Authenticator, Token


def create_security_router(injector: Injector) -> APIRouter:

    authenticator: Authenticator = injector.get(Authenticator)

    router: APIRouter = APIRouter(tags=["Security"], include_in_schema=False)

    router.add_api_route(
        "/token",
        authenticator.login_for_access_token,
        methods=["POST"],
        response_model=Token,
    )

    return router
