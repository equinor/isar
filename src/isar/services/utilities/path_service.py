from datetime import datetime
from pathlib import Path
from uuid import UUID


class PathService:
    """
    Class containing functionality for interaction with the pathlib library.
    """

    def __init__(
        self, base_path: Path = Path("raw/data/OMNIA COLLABORATIVE SERVICES/")
    ):
        self.base_path = base_path

    def get_upload_location(
        self,
        plant_code: str,
        timestamp: datetime,
        robot_id: str,
        inspection_type: str,
        mission_id: UUID,
        file_name: str,
    ) -> Path:
        """
        :param plant_code: Plant code as defined in SAP
        :param timestamp: Timestamp of the inspection (only year, month and day is used)
        :param robot_id: Unique ID of the robot used for inspection
        :param inspection_type: [ground, air, subsea]
        :param mission_id: Unique ID for the current mission
        :param file_name: Generated name for the inspection results
        :return: A path to be used for storage in blob storage
        """
        return self.base_path.joinpath(
            plant_code,
            "internal",
            str(timestamp.year),
            str(timestamp.month),
            str(timestamp.day),
            robot_id,
            str(mission_id),
            inspection_type,
            file_name,
        )

    def get_mission_metadata_location(
        self, plant_code: str, timestamp: datetime, robot_id: str, mission_id: UUID
    ) -> Path:
        """
        :param plant_code: Plant code as defined in SAP
        :param timestamp: Timestamp of the inspection (only year, month and day is used)
        :param robot_id: Unique ID of the robot used for inspection
        :param mission_id:
        :return: A path to be used for storage of metadata in blob storage
        """
        return self.base_path.joinpath(
            plant_code,
            "internal",
            str(timestamp.year),
            str(timestamp.month),
            str(timestamp.day),
            robot_id,
            str(mission_id),
            str(mission_id) + ".json",
        )
