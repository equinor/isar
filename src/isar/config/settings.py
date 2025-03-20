import os
from importlib.resources import as_file, files
from typing import Any, List, Optional

from dotenv import load_dotenv
from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from isar.config import predefined_missions
from robot_interface.models.robots.robot_model import RobotModel
from robot_interface.telemetry.payloads import DocumentInfo


class Settings(BaseSettings):
    def __init__(self) -> None:
        try:
            source = files("isar").joinpath("config").joinpath("settings.env")
            with as_file(source) as eml:
                env_file = eml
        except ModuleNotFoundError:
            env_file = None
        super().__init__(_env_file=env_file)

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
    FSM_SLEEP_TIME: float = Field(default=0.1)

    # Location of JSON files containing predefined missions for the Local Planner to use
    path: str = os.path.dirname(predefined_missions.__file__)
    PREDEFINED_MISSIONS_FOLDER: str = Field(default=path + "/")

    # Name of default map transformation
    DEFAULT_MAP: str = Field(default="default_map")

    # Location of JSON files containing predefined maps
    MAPS_FOLDER: str = Field(default="src/isar/config/maps/")

    # Determines the number of state transitions that are kept in the log
    STATE_TRANSITIONS_LOG_LENGTH: int = Field(default=20)

    # Number of attempts to initiate a mission before cancelling
    INITIATE_FAILURE_COUNTER_LIMIT: int = Field(default=10)

    # Number of attempts to request a task status in monitor before cancelling
    REQUEST_STATUS_FAILURE_COUNTER_LIMIT: int = Field(default=3)

    # Time allocated to reconnect when failing to retrieve status due to communication
    # issues
    REQUEST_STATUS_COMMUNICATION_RECONNECT_DELAY: float = Field(default=10)

    # Number of attempts to stop the robot before giving up
    STOP_ROBOT_ATTEMPTS_LIMIT: int = Field(default=3)

    # Number of attempts to stop the robot before giving up
    UPLOAD_FAILURE_ATTEMPTS_LIMIT: int = Field(default=10)

    # Number of attempts to stop the robot before giving up
    UPLOAD_FAILURE_MAX_WAIT: int = Field(default=60)

    # ISAR telemetry intervals
    ROBOT_STATUS_PUBLISH_INTERVAL: float = Field(default=1)
    ROBOT_HEARTBEAT_PUBLISH_INTERVAL: float = Field(default=1)
    ROBOT_INFO_PUBLISH_INTERVAL: float = Field(default=5)
    ROBOT_API_STATUS_POLL_INTERVAL: float = Field(default=5)

    # FastAPI host
    API_HOST_VIEWED_EXTERNALLY: str = Field(default="0.0.0.0")

    # FastAPI port
    API_PORT: int = Field(default=3000)

    # Determines how long delay time should be allowed before returning home
    RETURN_HOME_DELAY: int = Field(default=10)

    # Determines which mission planner module is used by ISAR
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
    AUTHENTICATION_ENABLED: bool = Field(default=True)

    # Tenant ID for the Azure tenant with your Azure Active Directory application
    AZURE_TENANT_ID: str = Field(default="3aa4a235-b6e2-48d5-9195-7fcf05b459b0")

    # Client ID for ISAR
    AZURE_CLIENT_ID: str = Field(default="fd384acd-5c1b-4c44-a1ac-d41d720ed0fe")
    # If AZURE_CLIENT_ID is set as an environment variable, overwrite this despite missing prefix.
    # This is done to avoid double config of ISAR_AZURE_CLIENT_ID and AZURE_CLIENT_ID.
    # We need the latter as an environment variable for the EnvironmentCredential method for AzureAD.
    azure_client_id_name: str = "AZURE_CLIENT_ID"
    if os.environ.get(azure_client_id_name) is not None:
        print("Using environment variable for AZURE_CLIENT_ID")
        AZURE_CLIENT_ID = os.environ[azure_client_id_name]

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
    KEYVAULT_NAME: str = Field(default="IsarDevKv")

    # Determines whether inspections are uploaded asynchronously or get_inspections in robotinterface
    UPLOAD_INSPECTIONS_ASYNC: bool = Field(default=False)

    # URL to storage account for Azure Blob Storage
    BLOB_STORAGE_ACCOUNT: str = Field(default="eqrobotdevstorage")

    # Name of blob container in Azure Blob Storage [slimm test]
    BLOB_CONTAINER: str = Field(default="test")

    # Client ID for SLIMM App Registration
    SLIMM_CLIENT_ID: str = Field(default="c630ca4d-d8d6-45ab-8cc6-68a363d0de9e")

    # Scope for access to SLIMM Ingestion API
    SLIMM_APP_SCOPE: str = Field(default=".default")

    # URL for SLIMM endpoint
    SLIMM_API_URL: str = Field(
        default="https://scinspectioningestapitest.azurewebsites.net/Ingest"
    )

    # Whether the results should be copied directly into the SLIMM datalake or only the
    # metadata
    COPY_FILES_TO_SLIMM_DATALAKE: bool = Field(default=False)

    # The configuration of this section is tightly coupled with the metadata that is
    # submitted with the results once they have been uploaded.

    # Four digit code indicating facility
    PLANT_CODE: str = Field(default="1210")

    # Name of the facility the robot is operating in
    PLANT_NAME: str = Field(default="Huldra")

    # Shortname of the facility the robot is operating in
    PLANT_SHORT_NAME: str = Field(default="HUA")

    # Country the robot is operating in
    COUNTRY: str = Field(default="Norway")

    # Type of robot ISAR is monitoring
    ROBOT_TYPE: str = Field(default="robot")

    # Name of robot
    ROBOT_NAME: str = Field(default="Placebot")

    # Unique identifier for this ISAR instance. Note that this should be a generated UUID.
    ISAR_ID: str = Field(default="00000000-0000-0000-0000-000000000000")

    # Serial number of the robot ISAR is connected to
    SERIAL_NUMBER: str = Field(default="0001")

    # Info about robot documentation
    DOCUMENTATION: List[DocumentInfo] = Field(default=[])

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
    TOPIC_ISAR_STATUS: str = Field(default="status", validate_default=True)
    TOPIC_ISAR_MISSION: str = Field(default="mission", validate_default=True)
    TOPIC_ISAR_TASK: str = Field(default="task", validate_default=True)
    TOPIC_ISAR_INSPECTION_RESULT: str = Field(
        default="inspection_result", validate_default=True
    )
    TOPIC_ISAR_ROBOT_INFO: str = Field(default="robot_info", validate_default=True)
    TOPIC_ISAR_ROBOT_HEARTBEAT: str = Field(
        default="robot_heartbeat", validate_default=True
    )

    # Logging

    #   Log handlers
    # Determines which log handlers are used by ISAR
    # Multiple log handlers can be chosen
    # Each handler will be called when logging
    # Selecting a different log handler than local may require certain access rights:
    #    - The Azure AI logger requires the 'APPLICATIONINSIGHTS_CONNECTION_STRING' to be set as an environment variable.
    LOG_HANDLER_LOCAL_ENABLED: bool = Field(default=True)
    LOG_HANDLER_APPLICATION_INSIGHTS_ENABLED: bool = Field(default=False)

    #   Log levels
    API_LOG_LEVEL: str = Field(default="INFO")
    MAIN_LOG_LEVEL: str = Field(default="INFO")
    MQTT_LOG_LEVEL: str = Field(default="INFO")
    STATE_MACHINE_LOG_LEVEL: str = Field(default="INFO")
    UPLOADER_LOG_LEVEL: str = Field(default="INFO")
    CONSOLE_LOG_LEVEL: str = Field(default="INFO")
    URLLIB3_LOG_LEVEL: str = Field(default="WARNING")
    UVICORN_LOG_LEVEL: str = Field(default="WARNING")
    AZURE_LOG_LEVEL: str = Field(default="WARNING")

    LOG_LEVELS: dict = Field(default={})

    REQUIRED_ROLE: str = Field(default="Mission.Control")

    @field_validator("LOG_LEVELS")
    @classmethod
    def set_log_levels(cls, v: Any, info: ValidationInfo) -> dict:
        return {
            "api": info.data["API_LOG_LEVEL"],
            "main": info.data["MAIN_LOG_LEVEL"],
            "mqtt": info.data["MQTT_LOG_LEVEL"],
            "state_machine": info.data["STATE_MACHINE_LOG_LEVEL"],
            "uploader": info.data["UPLOADER_LOG_LEVEL"],
            "console": info.data["CONSOLE_LOG_LEVEL"],
            "urllib3": info.data["URLLIB3_LOG_LEVEL"],
            "uvicorn": info.data["UVICORN_LOG_LEVEL"],
            "azure": info.data["AZURE_LOG_LEVEL"],
        }

    @field_validator(
        "TOPIC_ISAR_STATUS",
        "TOPIC_ISAR_MISSION",
        "TOPIC_ISAR_TASK",
        "TOPIC_ISAR_ROBOT_INFO",
        "TOPIC_ISAR_ROBOT_HEARTBEAT",
        "TOPIC_ISAR_INSPECTION_RESULT",
    )
    @classmethod
    def prefix_isar_topics(cls, v: Any, info: ValidationInfo):
        return f"isar/{info.data['ISAR_ID']}/{v}"

    model_config = SettingsConfigDict(
        env_prefix="ISAR_",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


load_dotenv()
settings = Settings()


class RobotSettings(BaseSettings):
    def __init__(self) -> None:
        try:
            source = (
                files(f"{settings.ROBOT_PACKAGE}")
                .joinpath("config")
                .joinpath("settings.env")
            )
            with as_file(source) as eml:
                env_file = eml
        except ModuleNotFoundError:
            env_file = None
        super().__init__(_env_file=env_file)

    # ISAR steps the robot is capable of performing
    # This should be set in the robot package settings.env file
    CAPABILITIES: List[str] = Field(default=["take_image"])

    # Model of the robot which ISAR is connected to
    # This should be set in the robot package settings.env file
    ROBOT_MODEL: RobotModel = Field(default=RobotModel.Robot)  # type: ignore

    # Valid arm poses that the robot may utilize
    # This should be set in the robot package settings.env file
    # Note that if the robot does not support moving an arm this will be None and
    # the functionality will be unavailable
    VALID_ARM_POSES: Optional[List[str]] = Field(default=None)
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


robot_settings = RobotSettings()
