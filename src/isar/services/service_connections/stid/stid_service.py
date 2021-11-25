import logging
from typing import Optional

from azure.identity import DefaultAzureCredential
from injector import inject
from requests import Response

from isar.config import config
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.service_connections.request_handler import RequestHandler
from robot_interface.models.geometry.frame import Frame
from robot_interface.models.geometry.position import Position


class StidService:
    @inject
    def __init__(self, request_handler: RequestHandler):
        self.request_handler: RequestHandler = request_handler
        self.credentials: DefaultAzureCredential = (
            AzureCredentials.get_azure_credentials()
        )
        self.logger = logging.getLogger("api")

    def tag_position(self, tag: str) -> Optional[Position]:
        client_id: str = config.get("service_connections", "stid_client_id")
        scope: str = config.get("service_connections", "stid_app_scope")
        request_scope: str = f"{client_id}/{scope}"

        token: str = self.credentials.get_token(request_scope).token

        stid_url: str = config.get("service_connections", "stid_api_url")
        plant_name: str = config.get("service_connections", "stid_plant_name")
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

        return Position(x=x_coord, y=y_coord, z=z_coord, frame=Frame.Asset)
