from dataclasses import dataclass

map_echo_hub_api_to_metadata_keys = {
    "name": "mission_name",
    "createdAt": "mission_created_at",
    "lastModified": "mission_last_modified",
    "robotOperator": "robot_operator",
}


@dataclass
class AdditionalMetadata:
    camera_type: str = ""
    mission_name: str = ""
    mission_created_at: str = ""
    mission_last_modified: str = ""
    robot_operator: str = ""
