import json
import logging

from azure.identity import DefaultAzureCredential
from dependency_injector.wiring import inject
from requests import HTTPError, RequestException
from requests_toolbelt import MultipartEncoder

from isar.config.settings import settings
from isar.services.auth.azure_credentials import AzureCredentials
from isar.services.service_connections.request_handler import RequestHandler
from isar.storage.storage_interface import StorageException, StorageInterface
from isar.storage.utilities import get_filename
from robot_interface.models.inspection.inspection import Inspection, ThermalVideo, Video
from robot_interface.models.mission.mission import Mission


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

    def store(self, inspection: Inspection, mission: Mission) -> str:
        filename: str = get_filename(
            inspection=inspection,
        )
        filename = f"{filename}.{inspection.metadata.file_type}"
        if type(inspection) in [Video, ThermalVideo]:
            inspection_path = self._store_video(filename, inspection, mission)
        else:
            inspection_path = self._store_image(filename, inspection, mission)
        return inspection_path

    def _store_image(
        self, filename: str, inspection: Inspection, mission: Mission
    ) -> str:
        multiform_body: MultipartEncoder = self._construct_multiform_request_image(
            filename=filename, inspection=inspection, mission=mission
        )
        request_url: str = f"{self.url}/UploadSingleImage"
        inspection_path = self._ingest(
            inspection=inspection,
            multiform_body=multiform_body,
            request_url=request_url,
        )
        return inspection_path

    def _store_video(
        self, filename: str, inspection: Inspection, mission: Mission
    ) -> str:
        multiform_body: MultipartEncoder = self._construct_multiform_request_video(
            filename=filename, inspection=inspection, mission=mission
        )
        request_url = f"{self.url}/UploadSingleVideo"
        inspection_path = self._ingest(
            inspection=inspection,
            multiform_body=multiform_body,
            request_url=request_url,
        )
        return inspection_path

    def _ingest(
        self,
        inspection: Inspection,
        multiform_body: MultipartEncoder,
        request_url: str,
    ) -> str:
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
            self.logger.info("SLIMM upload GUID: %s", guid)
        except (RequestException, HTTPError) as e:
            self.logger.warning(
                f"Failed to upload inspection: {inspection.id} to SLIMM due to a "
                f"request exception"
            )
            raise StorageException from e
        data = json.loads(response.content)
        return data["guid"]

    @staticmethod
    def _construct_multiform_request_image(
        filename: str, inspection: Inspection, mission: Mission
    ) -> MultipartEncoder:
        array_of_orientation = (
            inspection.metadata.pose.orientation.to_quat_array().tolist()
        )
        multiform_body: MultipartEncoder = MultipartEncoder(
            fields={
                "PlantFacilitySAPCode": settings.PLANT_CODE,
                "InstCode": settings.PLANT_SHORT_NAME,
                "InternalClassification": settings.DATA_CLASSIFICATION,
                "IsoCountryCode": "NO",
                "Geodetic.CoordinateReferenceSystemCode": settings.COORDINATE_REFERENCE_SYSTEM,  # noqa: E501
                "Geodetic.VerticalCoordinateReferenceSystemCode": settings.VERTICAL_REFERENCE_SYSTEM,  # noqa: E501
                "Geodetic.OrientationReferenceSystem": settings.MEDIA_ORIENTATION_REFERENCE_SYSTEM,  # noqa: E501
                "SensorCarrier.SensorCarrierId": settings.ISAR_ID,
                "SensorCarrier.ModelName": settings.ROBOT_TYPE,
                "Mission.MissionId": mission.id,
                "Mission.Client": "Equinor",
                "ImageMetadata.Timestamp": inspection.metadata.start_time.isoformat(),  # noqa: E501
                "ImageMetadata.X": str(inspection.metadata.pose.position.x),
                "ImageMetadata.Y": str(inspection.metadata.pose.position.y),
                "ImageMetadata.Z": str(inspection.metadata.pose.position.z),
                "ImageMetadata.CameraOrientation1": str(array_of_orientation[0]),
                "ImageMetadata.CameraOrientation2": str(array_of_orientation[1]),
                "ImageMetadata.CameraOrientation3": str(array_of_orientation[2]),
                "ImageMetadata.CameraOrientation4": str(array_of_orientation[3]),
                "ImageMetadata.Description": (
                    inspection.metadata.inspection_description
                    if inspection.metadata.inspection_description
                    else "N/A"
                ),
                "ImageMetadata.FunctionalLocation": (
                    inspection.metadata.tag_id  # noqa: E501
                    if inspection.metadata.tag_id
                    else "N/A"
                ),
                "Filename": filename,
                "AttachedFile": (filename, inspection.data),
            }
        )
        return multiform_body

    @staticmethod
    def _construct_multiform_request_video(
        filename: str,
        inspection: Inspection,
        mission: Mission,
    ) -> MultipartEncoder:
        array_of_orientation = (
            inspection.metadata.pose.orientation.to_quat_array().tolist()
        )
        multiform_body: MultipartEncoder = MultipartEncoder(
            fields={
                "PlantFacilitySAPCode": settings.PLANT_CODE,
                "InstCode": settings.PLANT_SHORT_NAME,
                "InternalClassification": settings.DATA_CLASSIFICATION,
                "IsoCountryCode": "NO",
                "Geodetic.CoordinateReferenceSystemCode": settings.COORDINATE_REFERENCE_SYSTEM,  # noqa: E501
                "Geodetic.VerticalCoordinateReferenceSystemCode": settings.VERTICAL_REFERENCE_SYSTEM,  # noqa: E501
                "Geodetic.OrientationReferenceSystem": settings.MEDIA_ORIENTATION_REFERENCE_SYSTEM,  # noqa: E501
                "SensorCarrier.SensorCarrierId": settings.ISAR_ID,
                "SensorCarrier.ModelName": settings.ROBOT_TYPE,
                "Mission.MissionId": mission.id,
                "Mission.Client": "Equinor",
                "VideoMetadata.Timestamp": inspection.metadata.start_time.isoformat(),  # noqa: E501
                # Converting to int because SLIMM expects an int, while we use floats in operations.
                "VideoMetadata.Duration": str(int(inspection.metadata.duration)),  # type: ignore
                "VideoMetadata.X": str(inspection.metadata.pose.position.x),
                "VideoMetadata.Y": str(inspection.metadata.pose.position.y),
                "VideoMetadata.Z": str(inspection.metadata.pose.position.z),
                "VideoMetadata.CameraOrientation1": str(array_of_orientation[0]),
                "VideoMetadata.CameraOrientation2": str(array_of_orientation[1]),
                "VideoMetadata.CameraOrientation3": str(array_of_orientation[2]),
                "VideoMetadata.CameraOrientation4": str(array_of_orientation[3]),
                "VideoMetadata.Description": (
                    inspection.metadata.inspection_description
                    if inspection.metadata.inspection_description
                    else "N/A"
                ),
                "VideoMetadata.FunctionalLocation": (
                    inspection.metadata.tag_id  # noqa: E501
                    if inspection.metadata.tag_id
                    else "N/A"
                ),
                "Filename": filename,
                "AttachedFile": (filename, inspection.data),
            }
        )
        return multiform_body
