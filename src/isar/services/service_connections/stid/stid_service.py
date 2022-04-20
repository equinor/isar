import logging
from typing import Optional

from alitra import Frame, Position
from azure.identity import DefaultAzureCredential
from injector import inject
from requests import Response

from isar.config.settings import settings
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.service_connections.request_handler import RequestHandler


class StidService:
    @inject
    def __init__(self, request_handler: RequestHandler):
        self.request_handler: RequestHandler = request_handler
        self.credentials: DefaultAzureCredential = (
            AzureCredentials.get_azure_credentials()
        )
        self.logger = logging.getLogger("api")

    def tag_position(self, tag: str) -> Optional[Position]:
        client_id: str = settings.STID_CLIENT_ID
        scope: str = settings.STID_APP_SCOPE
        request_scope: str = f"{client_id}/{scope}"

        token: str = self.credentials.get_token(request_scope).token

        stid_url: str = settings.STID_API_URL
        plant_name: str = settings.STID_PLANT_NAME
        request_url: str = f"{stid_url}/{plant_name}/tag"

        response: Response = self.request_handler.get(
            url=request_url,
            params={"tagNo": tag},
            headers={"Authorization": f"Bearer {token}"},
        )
        tag_metadata: dict = response.json()

        x_coord: float = tag_metadata["xCoordinate"] / 1000
        y_coord: float = tag_metadata["yCoordinate"] / 1000
        z_coord: float = tag_metadata["zCoordinate"] / 1000

        return Position(x=x_coord, y=y_coord, z=z_coord, frame=Frame("asset"))
