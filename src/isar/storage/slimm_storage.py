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
from isar.storage.utilities import get_filename
from robot_interface.models.inspection.inspection import Inspection, ThermalVideo, Video


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
        filename: str = get_filename(
            mission_id=metadata.mission_id,
            inspection_type=type(inspection).__name__,
            inspection_id=inspection.id,
        )
        filename = f"{filename}.{inspection.metadata.file_type}"
        if type(inspection) in [Video, ThermalVideo]:
            self._store_video(filename, inspection, metadata)
        else:
            self._store_image(filename, inspection, metadata)

    def _store_image(
        self, filename: str, inspection: Inspection, metadata: MissionMetadata
    ):
        multiform_body: MultipartEncoder = self._construct_multiform_request_image(
            filename=filename, inspection=inspection, metadata=metadata
        )
        request_url: str = f"{self.url}/UploadSingleImage"
        self._ingest(
            inspection=inspection,
            multiform_body=multiform_body,
            request_url=request_url,
        )
        return

    def _store_video(
        self, filename: str, inspection: Inspection, metadata: MissionMetadata
    ):
        multiform_body: MultipartEncoder = self._construct_multiform_request_video(
            filename=filename, inspection=inspection, metadata=metadata
        )
        request_url = f"{self.url}/UploadSingleVideo"
        self._ingest(
            inspection=inspection,
            multiform_body=multiform_body,
            request_url=request_url,
        )
        return

    def _ingest(
        self, inspection: Inspection, multiform_body: MultipartEncoder, request_url: str
    ):
        token: str = self.credentials.get_token(self.request_scope).token
        try:
            response = self.request_handler.post(
                url=request_url,
                data=multiform_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": multiform_body.content_type,
                },
            )
            guid = json.loads(response.text)["guid"]
            self.logger.info(f"SLIMM upload GUID: {guid}")
        except (RequestException, HTTPError) as e:
            self.logger.warning(
                f"Failed to upload inspection: {inspection.id} to SLIMM due to a "
                f"request exception"
            )
            raise StorageException from e

    @staticmethod
    def _construct_multiform_request_image(
        filename: str, inspection: Inspection, metadata: MissionMetadata
    ):
        array_of_orientation = (
            inspection.metadata.pose.orientation.to_quat_array().tolist()
        )
        multiform_body: MultipartEncoder = MultipartEncoder(
            fields={
                "PlantFacilitySAPCode": metadata.plant_code,
                "InstCode": metadata.plant_short_name,
                "InternalClassification": metadata.data_classification,
                "IsoCountryCode": "NO",
                "Geodetic.CoordinateReferenceSystemCode": metadata.coordinate_reference_system,  # noqa: E501
                "Geodetic.VerticalCoordinateReferenceSystemCode": metadata.vertical_reference_system,  # noqa: E501
                "Geodetic.OrientationReferenceSystem": metadata.media_orientation_reference_system,  # noqa: E501
                "SensorCarrier.SensorCarrierId": metadata.isar_id,
                "SensorCarrier.ModelName": metadata.robot_model,
                "Mission.MissionId": metadata.mission_id,
                "Mission.Client": "Equinor",
                "ImageMetadata.Timestamp": inspection.metadata.start_time.isoformat(),  # noqa: E501
                "ImageMetadata.X": str(inspection.metadata.pose.position.x),
                "ImageMetadata.Y": str(inspection.metadata.pose.position.y),
                "ImageMetadata.Z": str(inspection.metadata.pose.position.z),
                "ImageMetadata.CameraOrientation1": str(array_of_orientation[0]),
                "ImageMetadata.CameraOrientation2": str(array_of_orientation[1]),
                "ImageMetadata.CameraOrientation3": str(array_of_orientation[2]),
                "ImageMetadata.CameraOrientation4": str(array_of_orientation[3]),
                "ImageMetadata.AnalysisMethods": str(inspection.metadata.analysis),
                "ImageMetadata.Description": str(inspection.metadata.additional),
                "ImageMetadata.FunctionalLocation": inspection.metadata.tag_id  # noqa: E501
                if inspection.metadata.tag_id
                else "NA",
                "Filename": filename,
                "AttachedFile": (filename, inspection.data),
            }
        )
        return multiform_body

    @staticmethod
    def _construct_multiform_request_video(
        filename: str,
        inspection: Inspection,
        metadata: MissionMetadata,
    ):
        array_of_orientation = (
            inspection.metadata.pose.orientation.to_quat_array().tolist()
        )
        multiform_body: MultipartEncoder = MultipartEncoder(
            fields={
                "PlantFacilitySAPCode": metadata.plant_code,
                "InstCode": metadata.plant_short_name,
                "InternalClassification": metadata.data_classification,
                "IsoCountryCode": "NO",
                "Geodetic.CoordinateReferenceSystemCode": metadata.coordinate_reference_system,  # noqa: E501
                "Geodetic.VerticalCoordinateReferenceSystemCode": metadata.vertical_reference_system,  # noqa: E501
                "Geodetic.OrientationReferenceSystem": metadata.media_orientation_reference_system,  # noqa: E501
                "SensorCarrier.SensorCarrierId": metadata.isar_id,
                "SensorCarrier.ModelName": metadata.robot_model,
                "Mission.MissionId": metadata.mission_id,
                "Mission.Client": "Equinor",
                "VideoMetadata.Timestamp": inspection.metadata.start_time.isoformat(),  # noqa: E501
                "VideoMetadata.Duration": str(inspection.metadata.duration),  # type: ignore
                "VideoMetadata.X": str(inspection.metadata.pose.position.x),
                "VideoMetadata.Y": str(inspection.metadata.pose.position.y),
                "VideoMetadata.Z": str(inspection.metadata.pose.position.z),
                "VideoMetadata.CameraOrientation1": str(array_of_orientation[0]),
                "VideoMetadata.CameraOrientation2": str(array_of_orientation[1]),
                "VideoMetadata.CameraOrientation3": str(array_of_orientation[2]),
                "VideoMetadata.CameraOrientation4": str(array_of_orientation[3]),
                "VideoMetadata.AnalysisMethods": str(inspection.metadata.analysis),
                "VideoMetadata.Description": str(inspection.metadata.additional),
                "VideoMetadata.FunctionalLocation": inspection.metadata.tag_id  # noqa: E501
                if inspection.metadata.tag_id
                else "NA",
                "Filename": filename,
                "AttachedFile": (filename, inspection.data),
            }
        )
        return multiform_body
