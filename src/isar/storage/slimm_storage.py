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
                params={"DataType": "still"},
                data=multiform_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": multiform_body.content_type,
                },
            )
        except (RequestException, HTTPError) as e:
            self.logger.warning(
                f"Failed to upload inspection: {inspection.id} to SLIMM due to a "
                f"request exception"
            )
            raise StorageException from e

    @staticmethod
    def _construct_multiform_request(filename, inspection, metadata):
        array_of_orientation = (
            inspection.metadata.time_indexed_pose.pose.orientation.to_quat_array().tolist()
        )
        multiform_body: MultipartEncoder = MultipartEncoder(
            fields={
                "SchemaMetadata.Mission.MissionId": metadata.mission_id,
                "SchemaMetadata.Mission.StartDate": metadata.mission_date.isoformat(),
                "SchemaMetadata.Mission.EndDate": metadata.mission_date.isoformat(),
                "SchemaMetadata.Geodetic.CoordinateReferenceSystemCode": metadata.coordinate_reference_system,  # noqa: E501
                "SchemaMetadata.Geodetic.VerticalCoordinateReferenceSystemCode": metadata.vertical_reference_system,  # noqa: E501
                "SchemaMetadata.Geodetic.OrientationReferenceSystem": metadata.media_orientation_reference_system,  # noqa: E501
                "SchemaMetadata.SensorCarrier.Id": metadata.robot_id,
                "SchemaMetadata.InternalClassification": metadata.data_classification,
                "SchemaMetadata.PlantFacilitySAPCode": metadata.plant_code,
                "SchemaMetadata.Mission.Client": "Equinor",
                "SchemaMetadata.IsoCountryCode": "NO",
                "AttachedFileMetadata.X": str(
                    inspection.metadata.time_indexed_pose.pose.position.x
                ),
                "AttachedFileMetadata.Y": str(
                    inspection.metadata.time_indexed_pose.pose.position.y
                ),
                "AttachedFileMetadata.Z": str(
                    inspection.metadata.time_indexed_pose.pose.position.z
                ),
                "AttachedFileMetadata.CameraOrientation[0]": str(
                    array_of_orientation[0]
                ),
                "AttachedFileMetadata.CameraOrientation[1]": str(
                    array_of_orientation[1]
                ),
                "AttachedFileMetadata.CameraOrientation[2]": str(
                    array_of_orientation[2]
                ),
                "AttachedFileMetadata.CameraOrientation[3]": str(
                    array_of_orientation[3]
                ),
                "AttachedFileMetadata.FunctionalLocation": inspection.metadata.tag_id  # noqa: E501
                if inspection.metadata.tag_id
                else "NA",
                "AttachedFileMetadata.Timestamp": inspection.metadata.start_time.isoformat(),  # noqa: E501
                "AttachedFile": (filename, inspection.data),
            }
        )
        return multiform_body
