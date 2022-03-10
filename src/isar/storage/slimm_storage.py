import json
import logging

from azure.identity import DefaultAzureCredential
from injector import inject
from requests import HTTPError, RequestException
from requests_toolbelt import MultipartEncoder

from isar.config.settings import settings
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.service_connections.request_handler import RequestHandler
from isar.storage.storage_interface import StorageException, StorageInterface
from isar.storage.utilities import get_filename, get_inspection_type
from robot_interface.models.inspection.inspection import Inspection


class SlimmStorage(StorageInterface):
    @inject
    def __init__(self, request_handler: RequestHandler) -> None:
        self.request_handler: RequestHandler = request_handler
        self.logger = logging.getLogger("uploader")

        self.credentials: DefaultAzureCredential = (
            AzureCredentials.get_azure_credentials()
        )

        client_id: str = settings.SLIMM_CLIENT_ID
        scope: str = settings.SLIMM_APP_SCOPE
        self.request_scope: str = f"{client_id}/{scope}"

        self.url: str = settings.SLIMM_API_URL

    def store(self, inspection: Inspection, metadata: MissionMetadata):
        token: str = self.credentials.get_token(self.request_scope).token

        request_url: str = f"{self.url}/UploadSingleFile"

        inspection_type: str = get_inspection_type(inspection=inspection)
        filename: str = get_filename(
            mission_id=metadata.mission_id,
            inspection_type=inspection_type,
            inspection_id=inspection.id,
        )
        filename_with_ending: str = f"{filename}.{inspection.metadata.file_type}"

        multiform_body: MultipartEncoder = self._construct_multiform_request(
            filename=filename_with_ending, inspection=inspection, metadata=metadata
        )

        self._ingest(
            inspection=inspection,
            multiform_body=multiform_body,
            request_url=request_url,
            token=token,
        )

    def _ingest(self, inspection, multiform_body, request_url, token):
        try:
            self.request_handler.post(
                url=request_url,
                params={
                    "CopyFilesToSlimmDatalake": settings.COPY_FILES_TO_SLIMM_DATALAKE
                },
                data=multiform_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": multiform_body.content_type,
                },
            )
        except (RequestException, HTTPError) as e:
            self.logger.warning(
                f"Failed to upload inspection: {inspection.id} to SLIMM due to a request exception"
            )
            raise StorageException from e

    @staticmethod
    def _construct_multiform_request(filename, inspection, metadata):
        multiform_body: MultipartEncoder = MultipartEncoder(
            fields={
                "additional_metadata": json.dumps(
                    {
                        "plant_name": metadata.plant_name,
                        "mission_date": metadata.mission_date.isoformat(),
                        "mission_id": metadata.mission_id,
                        "robot_id": metadata.robot_id,
                    }
                ),
                "coordinate_reference_system": metadata.coordinate_reference_system,
                "vertical_reference_system": metadata.vertical_reference_system,
                "media_orientation_reference_system": metadata.media_orientation_reference_system,
                "data_classification": metadata.data_classification,
                "plant_code": metadata.plant_code,
                "attached_file_navigation.Filename": filename,
                "attached_file_navigation.ContentSize": str(len(inspection.data)),
                "attached_file_navigation.X": str(
                    inspection.metadata.time_indexed_pose.pose.position.x
                ),
                "attached_file_navigation.Y": str(
                    inspection.metadata.time_indexed_pose.pose.position.y
                ),
                "attached_file_navigation.Z": str(
                    inspection.metadata.time_indexed_pose.pose.position.z
                ),
                "attached_file_navigation.AdditionalMediaMetadata": json.dumps(
                    {
                        "orientation": inspection.metadata.time_indexed_pose.pose.orientation.to_list()
                    }
                ),
                "attached_file_navigation.FunctionalLocation": inspection.metadata.tag_id
                if inspection.metadata.tag_id
                else "NA",
                "attached_file_navigation.Timestamp": inspection.metadata.start_time.isoformat(),
                "attached_file": (filename, inspection.data),
            }
        )
        return multiform_body
