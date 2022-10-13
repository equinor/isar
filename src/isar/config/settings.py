import importlib.resources as pkg_resources
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    # Determines which robot package ISAR will attempt to import
    # Name must match with an installed python package in the local environment
    ROBOT_PACKAGE: str = Field(default="isar_robot")

    # Determines the local path in which results from missions are stored
    LOCAL_STORAGE_PATH: str = Field(default="./results")

    # Timeout in seconds for direct HTTP requests made through the RequestHandler
    REQUEST_TIMEOUT: int = Field(default=30)

    # Timeout in seconds for checking whether there is a message on a queue
    QUEUE_TIMEOUT: int = Field(default=10)

    # Sleep time for while loops in the finite state machine in seconds
    # The sleep is used to throttle the system on every iteration in the loop
    FSM_SLEEP_TIME: int = Field(default=0.1)

    # Location of JSON files containing predefined missions for the Local Planner to use
    PREDEFINED_MISSIONS_FOLDER: str = Field(
        default="src/isar/config/predefined_missions/"
    )

    # Name of default map transformation
    DEFAULT_MAP: str = Field(default="default_map")

    # Location of JSON files containing predefined maps
    MAPS_FOLDER: str = Field(default="src/isar/config/maps/")

    # Determines the number of state transitions that are kept in the log
    STATE_TRANSITIONS_LOG_LENGTH: int = Field(default=20)

    # Number of attempts to initiate a step before cancelling
    INITIATE_STEP_FAILURE_COUNTER_LIMIT: int = Field(default=10)

    # Number of attempts to stop the robot before giving up
    STOP_ROBOT_ATTEMPTS_LIMIT: int = Field(default=10)

    # Number of attempts to stop the robot before giving up
    UPLOAD_FAILURE_ATTEMPTS_LIMIT: int = Field(default=10)

    # Number of attempts to stop the robot before giving up
    UPLOAD_FAILURE_MAX_WAIT: int = Field(default=60)

    # FastAPI host
    API_HOST: str = Field(default="0.0.0.0")

    # FastAPI port
    API_PORT: int = Field(default=3000)

    # Determines which mission planner module is used by ISAR
    # Options: [local echo]
    # Selecting a different mission planner module than local may require certain access
    # rights
    MISSION_PLANNER: str = Field(default="local")

    # Determines which task selector module is used by ISAR
    # Options: [sequential]
    TASK_SELECTOR: str = Field(default="sequential")

    # Determines which storage modules are used by ISAR
    # Multiple storage modules can be chosen
    # Each module will be called when storing results from inspections
    # Selecting a different storage module than local may require certain access rights
    STORAGE_LOCAL_ENABLED: bool = Field(default=True)
    STORAGE_BLOB_ENABLED: bool = Field(default=False)
    STORAGE_SLIMM_ENABLED: bool = Field(default=False)

    # Determines whether the MQTT publishing module should be enabled or not
    # The publishing module will attempt to connect to the MQTT broker configured in
    # "service_connections"
    # Options: [false true]
    MQTT_ENABLED: bool = Field(default=False)

    # Determines whether certificate based encryption will be used for the MQTT
    # communication.
    MQTT_SSL_ENABLED: bool = Field(default=True)

    # Determines whether authentication is enabled for the API or not
    # Enabling this requires certain resources available for OAuth2 authentication
    # Currently supported authentication is Azure AD
    # (https://github.com/Intility/fastapi-azure-auth)
    AUTHENTICATION_ENABLED: bool = Field(default=False)

    # Tenant ID for the Azure tenant with your Azure Active Directory application
    AZURE_TENANT_ID: str = Field(default="3aa4a235-b6e2-48d5-9195-7fcf05b459b0")

    # Client ID for the API client
    APP_CLIENT_ID: str = Field(default="68cca82d-84e7-495c-96b4-4c32509f2a46")

    # Client ID for the OpenAPI client
    OPENAPI_CLIENT_ID: str = Field(default="5f412c20-8c36-4c69-898f-d2b5051f5fb6")

    # MQTT username
    # The username and password is set by the MQTT broker and must be known in advance
    # The password should be set as an environment variable "MQTT_PASSWORD"
    # If the password is not set in the environment an empty string will be used
    MQTT_USERNAME: str = Field(default="isar")

    # MQTT host
    MQTT_HOST: str = Field(default="localhost")

    # MQTT port
    MQTT_PORT: int = Field(default=1883)

    # Keyvault name
    KEYVAULT: str = Field(default="EqRobotKeyVault")

    # URL to storage account for Azure Blob Storage
    BLOB_STORAGE_ACCOUNT_URL: str = Field(
        default="https://eqrobotdevstorage.blob.core.windows.net"
    )

    # Name of blob container in Azure Blob Storage [slimm test]
    BLOB_CONTAINER: str = Field(default="test")

    # Client ID for STID App Registration
    STID_CLIENT_ID: str = Field(default="1734406c-3449-4192-a50d-7c3a63d3f57d")

    # Scope for access to STID API
    STID_APP_SCOPE: str = Field(default=".default")

    # URL for STID endpoint
    STID_API_URL: str = Field(default="https://stidapi.equinor.com")

    # Plant name for the facility which STID should look for tags in
    STID_PLANT_NAME: str = Field(default="kaa")

    # Client ID for Echo App Registration
    ECHO_CLIENT_ID: str = Field(default="bf0b2569-e09c-42f0-8095-5a52a873eb7b")

    # Scope for access to Echo API
    ECHO_APP_SCOPE: str = Field(default=".default")

    # URL for Echo endpoint
    ECHO_API_URL: str = Field(default="https://echohubapi.equinor.com/api")

    # Client ID for SLIMM App Registration
    SLIMM_CLIENT_ID: str = Field(default="94c048cc-58e9-4570-85c0-4028c50ab6f3")

    # Scope for access to SLIMM Ingestion API
    SLIMM_APP_SCOPE: str = Field(default=".default")

    # URL for SLIMM endpoint
    SLIMM_API_URL: str = Field(
        default="https://slimmingestapitest.azurewebsites.net/SpatialIngest"
    )

    # Whether the results should be copied directly into the SLIMM datalake or only the
    # metadata
    COPY_FILES_TO_SLIMM_DATALAKE: bool = Field(default=False)

    # The configuration of this section is tightly coupled with the metadata that is
    # submitted with the results once they have been uploaded.

    # Four digit code indicating facility
    PLANT_CODE: str = Field(default="1320")

    # Name of the facility the robot is operating in
    PLANT_NAME: str = Field(default="Kårstø")

    # Shortname of the facility the robot is operating in
    PLANT_SHORT_NAME: str = Field(default="KAA")

    # Country the robot is operating in
    COUNTRY: str = Field(default="Norway")

    # Type of robot ISAR is monitoring
    ROBOT_TYPE: str = Field(default="robot")

    # Name or unique ID of robot
    ROBOT_ID: str = Field(default="R2-D2")

    # Data scheme the robot should adhere to
    # Options [DS0001]
    DATA_SCHEME: str = Field(default="DS0001")

    # Coordinate reference system of facility
    COORDINATE_REFERENCE_SYSTEM: str = Field(default="EQUINOR:4100001")

    # Vertical reference system of facility
    VERTICAL_REFERENCE_SYSTEM: str = Field(default="MSL")

    # Rotational representations of reported results
    # Options [quaternion]
    MEDIA_ORIENTATION_REFERENCE_SYSTEM: str = Field(default="quaternion")

    # Contractor who is responsible for robot missions
    CONTRACTOR: str = Field(default="equinor")

    # Timezone
    TIMEZONE: str = Field(default="UTC+00:00")

    # Data classification
    DATA_CLASSIFICATION: str = Field(default="internal")

    # List of MQTT Topics

    TOPIC_ISAR_ROBOT: str = Field(default="robot")

    TOPIC_ISAR_STATE: str = Field(default="state")

    TOPIC_ISAR_MISSION: str = Field(default="mission")

    TOPIC_ISAR_TASK: str = Field(default="task")

    TOPIC_ISAR_STEP: str = Field(default="step")

    API_LOG_LEVEL: str = Field(default="INFO")
    CONSOLE_LOG_LEVEL: str = Field(default="INFO")
    URLLIB3_LOG_LEVEL: str = Field(default="WARNING")
    UVICORN_LOG_LEVEL: str = Field(default="WARNING")
    STATE_MACHINE_LOG_LEVEL: str = Field(default="INFO")
    UPLOADER_LOG_LEVEL: str = Field(default="INFO")
    MAIN_LOG_LEVEL: str = Field(default="INFO")
    AZURE_LOG_LEVEL: str = Field(default="WARNING")

    LOG_LEVELS: dict = Field(default={})

    @validator("LOG_LEVELS", pre=True, always=True)
    def set_log_levels(cls, v, values) -> dict:
        return {
            "console": values["CONSOLE_LOG_LEVEL"],
            "api": values["API_LOG_LEVEL"],
            "urllib3": values["URLLIB3_LOG_LEVEL"],
            "uvicorn": values["UVICORN_LOG_LEVEL"],
            "state_machine": values["STATE_MACHINE_LOG_LEVEL"],
            "uploader": values["UPLOADER_LOG_LEVEL"],
            "main": values["MAIN_LOG_LEVEL"],
            "azure": values["AZURE_LOG_LEVEL"],
        }

    @validator(
        "TOPIC_ISAR_ROBOT",
        "TOPIC_ISAR_STATE",
        "TOPIC_ISAR_MISSION",
        "TOPIC_ISAR_TASK",
        "TOPIC_ISAR_STEP",
        pre=True,
        always=True,
    )
    def prefix_isar_topics(cls, v, values):
        return f"isar/{values['ROBOT_ID']}/{v}"

    class Config:
        with pkg_resources.path("isar.config", "settings.env") as path:
            package_path = path

        env_prefix = "ISAR_"
        env_file = package_path
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


class RobotSettings(BaseSettings):
    def __init__(self) -> None:
        try:
            with pkg_resources.path(
                f"{settings.ROBOT_PACKAGE}.config", "settings.env"
            ) as path:
                env_file_path = path
        except ModuleNotFoundError:
            env_file_path = None
        super().__init__(_env_file=env_file_path)

    CAPABILITIES: List[str] = Field(default=["drive_to_pose", "take_image"])

    class Config:
        env_file_encoding = "utf-8"
        case_sensitive = True


robot_settings = RobotSettings()
