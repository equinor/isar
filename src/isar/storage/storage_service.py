import json
from pathlib import Path
from typing import List, Union
from uuid import UUID

from injector import inject

from isar.config import config
from isar.models.mission import Mission
from isar.models.mission_metadata.mission_metadata import MissionMetadata
from isar.services.utilities.json_service import EnhancedJSONEncoder
from isar.storage.storage_interface import StorageInterface
from robot_interface.models.inspection.formats import Audio, Image, ThermalImage, Video
from robot_interface.models.inspection.inspection import (
    Inspection,
    InspectionMetadata,
    InspectionResult,
)
from robot_interface.models.inspection.references import (
    AudioReference,
    ImageReference,
    ThermalImageReference,
    VideoReference,
)


class StorageService:
    @inject
    def __init__(self, storage: StorageInterface):
        self.storage: StorageInterface = storage

    def store(
        self, mission_id: Union[UUID, int, str, None], result: InspectionResult
    ) -> None:
        sensor_sub_folder_name: str = self.get_sensor_sub_folder_name(result=result)
        filename: str = self.get_inspection_filename(
            mission_id=mission_id,
            sensor_sub_folder_name=sensor_sub_folder_name,
            inspection=result,
        )
        destination_path: Path = Path(
            f"{mission_id}/sensor_data/{sensor_sub_folder_name}/{filename}"
        )

        self.storage.store(data=result.data, path=destination_path)

    def store_metadata(
        self,
        mission: Mission,
    ) -> None:
        for inspection_type in [
            ImageReference,
            ThermalImageReference,
            AudioReference,
            VideoReference,
        ]:
            self.store_metadata_for_inspection_type(
                mission_id=mission.id,
                inspections=mission.inspections,
                inspection_type=inspection_type,
            )
        self.store_metadata_for_mission(mission=mission)

    def get_sensor_sub_folder_name(
        self, result: Union[InspectionResult, Inspection]
    ) -> str:
        if isinstance(result, Audio) or isinstance(result, AudioReference):
            return "audio"
        elif isinstance(result, Image) or isinstance(result, ImageReference):
            return "image"
        elif isinstance(result, ThermalImage) or isinstance(
            result, ThermalImageReference
        ):
            return "thermal"
        elif isinstance(result, Video) or isinstance(result, VideoReference):
            return "video"
        else:
            raise TypeError(
                "Inspection must be either Audio, Image, Video or a Reference to one of them"
            )

    def get_inspection_filename(
        self,
        mission_id: Union[UUID, int, str, None],
        sensor_sub_folder_name: str,
        inspection: Inspection,
    ) -> str:
        return f"{mission_id}_{sensor_sub_folder_name}_{inspection.id}.{inspection.metadata.file_type}"

    def store_metadata_for_inspection_type(
        self,
        mission_id: Union[UUID, int, str, None],
        inspections: List[Inspection],
        inspection_type: type,
    ) -> None:
        inspections_of_type: List[Inspection] = [
            inspection
            for inspection in inspections
            if inspection.__class__ is inspection_type
        ]
        if len(inspections_of_type) == 0:
            return

        metadata_dicts: List[dict] = []
        for inspection in inspections_of_type:
            inspection_dicts: List[dict] = self.inspection_metadata_to_dicts(
                mission_id=mission_id, inspection=inspection
            )
            metadata_dicts.extend(inspection_dicts)

        sensor_sub_folder_name: str = self.get_sensor_sub_folder_name(
            result=inspections_of_type[0]
        )
        filename: str = f"{mission_id}_{sensor_sub_folder_name}_NAVI.json"
        destination_path: Path = Path(
            f"{mission_id}/sensor_data/{sensor_sub_folder_name}/{filename}"
        )

        metadata_as_bytes: bytes = json.dumps(
            metadata_dicts, cls=EnhancedJSONEncoder, indent=4
        ).encode()

        self.storage.store(data=metadata_as_bytes, path=destination_path)

    def inspection_metadata_to_dicts(
        self,
        mission_id: Union[UUID, int, str, None],
        inspection: Inspection,
    ) -> List[dict]:
        sensor_sub_folder_name: str = self.get_sensor_sub_folder_name(inspection)
        inspection_metadata: InspectionMetadata = inspection.metadata

        if isinstance(inspection_metadata.time_indexed_pose, list):
            return list(
                map(
                    lambda time_and_pose: {
                        "timestamp": inspection_metadata.start_time,
                        "position": time_and_pose.pose.position.to_list(),
                        "orientation": time_and_pose.pose.orientation.to_list(),
                        "file_name": self.get_inspection_filename(
                            mission_id, sensor_sub_folder_name, inspection
                        ),
                        "time_from_start": str(
                            time_and_pose.time - inspection_metadata.start_time
                        ),
                        "tag": inspection_metadata.tag_id,
                        "additional_data": inspection_metadata.additional,
                    },
                    inspection_metadata.time_indexed_pose,
                )
            )
        else:
            return [
                {
                    "timestamp": inspection_metadata.start_time,
                    "position": inspection_metadata.time_indexed_pose.pose.position.to_list(),
                    "orientation": inspection_metadata.time_indexed_pose.pose.orientation.to_list(),
                    "file_name": self.get_inspection_filename(
                        mission_id, sensor_sub_folder_name, inspection
                    ),
                    "tag": inspection_metadata.tag_id,
                    "additional_data": inspection_metadata.additional,
                }
            ]

    def store_metadata_for_mission(self, mission: Mission) -> None:
        mission_metadata: MissionMetadata = mission.metadata
        mission_metadata.required_metadata.url = (
            f"{config.get('service_connections', 'blob_storage_account_url')}/"
            f"{config.get('service_connections', 'blob_container')}/{mission.id}"
        )

        filename: str = f"{mission.id}_META.json"
        destination_path: Path = Path(f"{mission.id}/{filename}")

        inspection_types_used = set()
        for inspection in mission.inspections:
            sensor_sub_folder_name: str = self.get_sensor_sub_folder_name(inspection)
            inspection_types_used.add(sensor_sub_folder_name)

        data_structure_dicts: List[dict] = [
            {
                "folder": f"/sensor_data/{inspection_type_str}",
                "navigation": f"/sensor_data/{inspection_type_str}/{mission.id}_{inspection_type_str}_NAVI.json",
            }
            for inspection_type_str in inspection_types_used
        ]

        metadata: dict = {
            "required_metadata": {
                "mission_id": mission_metadata.required_metadata.mission_id,
                "data_scheme": mission_metadata.required_metadata.data_scheme,
                "coordinate_reference_system": mission_metadata.required_metadata.coordinate_reference_system,
                "vertical_reference_system": mission_metadata.required_metadata.vertical_reference_system,
                "sensor_carrier_orientation_reference_system": mission_metadata.required_metadata.sensor_carrier_orientation_reference_system,
                "data_classification": mission_metadata.required_metadata.data_classification,
                "url": mission_metadata.required_metadata.url,
            },
            "recommended_metadata": {
                "date": mission_metadata.recommended_metadata.date,
                "sensor_carrier_id": mission_metadata.recommended_metadata.sensor_carrier_id,
                "sensor_carrier_type": mission_metadata.recommended_metadata.sensor_carrier_type,
                "plant_code": mission_metadata.recommended_metadata.plant_code,
                "plant_name": mission_metadata.recommended_metadata.plant_name,
                "country": mission_metadata.recommended_metadata.country,
                "contractor": mission_metadata.recommended_metadata.contractor,
                "mission_type": mission_metadata.recommended_metadata.mission_type,
            },
            "additional_metadata": {
                "camera_type": mission.metadata.additional_metadata.camera_type,
                "mission_name": mission.metadata.additional_metadata.mission_name,
                "mission_created_at": mission.metadata.additional_metadata.mission_created_at,
                "mission_last_modified": mission.metadata.additional_metadata.mission_last_modified,
                "robot_operator": mission.metadata.additional_metadata.robot_operator,
            },
            "data": data_structure_dicts,
        }

        metadata_as_bytes: bytes = json.dumps(
            metadata, cls=EnhancedJSONEncoder, indent=4
        ).encode()

        self.storage.store(data=metadata_as_bytes, path=destination_path)
