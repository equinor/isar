import logging
from logging import Logger
from importlib import import_module
from types import ModuleType
from typing import List, Union

from injector import Injector, Module, multiprovider, provider, singleton

from isar.apis.api import API
from isar.apis.schedule.drive_to import DriveTo
from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission
from isar.apis.security.authentication import Authenticator
from isar.config.keyvault.keyvault_service import Keyvault
from isar.config.settings import settings
from isar.mission_planner.echo_planner import EchoPlanner
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerInterface
from isar.models.communication.queues.queues import Queues
from isar.services.service_connections.mqtt.mqtt_client import (
    MqttClientInterface,
    MqttPublisher,
)
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.storage.blob_storage import BlobStorage
from isar.storage.local_storage import LocalStorage
from isar.storage.slimm_storage import SlimmStorage
from isar.storage.storage_interface import StorageInterface
from robot_interface.robot_interface import RobotInterface


class APIModule(Module):
    @provider
    @singleton
    def provide_api(
        self,
        authenticator: Authenticator,
        start_mission: StartMission,
        stop_mission: StopMission,
        drive_to: DriveTo,
    ) -> API:
        return API(authenticator, start_mission, stop_mission, drive_to)

    @provider
    @singleton
    def provide_drive_to(self, scheduling_utilities: SchedulingUtilities) -> DriveTo:
        return DriveTo(scheduling_utilities)

    @provider
    @singleton
    def provide_start_mission(
        self,
        mission_planner: MissionPlannerInterface,
        scheduling_utilities: SchedulingUtilities,
    ) -> StartMission:
        return StartMission(mission_planner, scheduling_utilities)

    @provider
    @singleton
    def provide_stop_mission(self, queues: Queues) -> StopMission:
        return StopMission(queues)


class AuthenticationModule(Module):
    @provider
    @singleton
    def provide_authenticator(self) -> Authenticator:
        return Authenticator()


class RobotModule(Module):
    @provider
    @singleton
    def provide_robot_interface(self) -> RobotInterface:
        robot_package_name: str = settings.ROBOT_PACKAGE
        robot: ModuleType = import_module(robot_package_name)
        return robot.robotinterface.Robot()  # type: ignore


class QueuesModule(Module):
    @provider
    @singleton
    def provide_queues(self) -> Queues:
        return Queues()


class RequestHandlerModule(Module):
    @provider
    @singleton
    def provide_request_handler(self) -> RequestHandler:
        return RequestHandler()


class BlobStorageModule(Module):
    @multiprovider
    @singleton
    def provide_blob_storage(self, keyvault: Keyvault) -> List[StorageInterface]:
        return [BlobStorage(keyvault)]


class LocalStorageModule(Module):
    @multiprovider
    @singleton
    def provide_local_storage(self) -> List[StorageInterface]:
        return [LocalStorage()]


class SlimmStorageModule(Module):
    @multiprovider
    @singleton
    def provide_slimm_storage(
        self, request_handler: RequestHandler
    ) -> List[StorageInterface]:
        return [SlimmStorage(request_handler=request_handler)]


class LocalPlannerModule(Module):
    @provider
    @singleton
    def provide_local_planner(self) -> MissionPlannerInterface:
        return LocalPlanner()


class EchoPlannerModule(Module):
    @provider
    @singleton
    def provide_echo_planner(
        self,
        request_handler: RequestHandler,
        stid_service: StidService,
    ) -> MissionPlannerInterface:
        return EchoPlanner(
            request_handler=request_handler,
            stid_service=stid_service,
        )


class StateMachineModule(Module):
    @provider
    @singleton
    def provide_state_machine(
        self,
        queues: Queues,
        robot: RobotInterface,
        mqtt_client: MqttClientInterface,
    ) -> StateMachine:
        return StateMachine(queues=queues, robot=robot, mqtt_client=mqtt_client)


class UtilitiesModule(Module):
    @provider
    @singleton
    def provide_scheduling_utilities(self, queues: Queues) -> SchedulingUtilities:
        return SchedulingUtilities(queues)


class ServiceModule(Module):
    @provider
    @singleton
    def provide_keyvault(self) -> Keyvault:
        return Keyvault(keyvault_name=settings.KEYVAULT)

    @provider
    @singleton
    def provide_stid_service(self, request_handler: RequestHandler) -> StidService:
        return StidService(request_handler=request_handler)


class MqttModule(Module):
    @provider
    @singleton
    def provide_mqtt_client(self, queues: Queues) -> MqttClientInterface:
        if settings.MQTT_ENABLED:
            return MqttPublisher(mqtt_queue=queues.mqtt_queue)
        return None


modules: dict[str, tuple[Module, Union[str, bool]]] = {
    "api": (APIModule, "required"),
    "authentication": (AuthenticationModule, "required"),
    "queues": (QueuesModule, "required"),
    "request_handler": (RequestHandlerModule, "required"),
    "robot": (RobotModule, settings.ROBOT_PACKAGE),
    "mission_planner": (
        {
            "default": LocalPlannerModule,
            "local": LocalPlannerModule,
            "echo": EchoPlannerModule,
        }[settings.MISSION_PLANNER],
        settings.MISSION_PLANNER,
    ),
    "service": (ServiceModule, "required"),
    "state_machine": (StateMachineModule, "required"),
    "storage_local": (LocalStorageModule, settings.STORAGE_LOCAL_ENABLED),
    "storage_blob": (BlobStorageModule, settings.STORAGE_BLOB_ENABLED),
    "storage_slimm": (SlimmStorageModule, settings.STORAGE_SLIMM_ENABLED),
    "mqtt": (MqttModule, "required"),
    "utilities": (UtilitiesModule, "required"),
}


def get_injector() -> Injector:
    injector_modules: List[Module] = []
    module_overview: str = ""

    for category, (module, config_option) in modules.items():
        if config_option:
            injector_modules.append(module)
        module_overview += (
            f"\n    {category:<15} : {config_option:<20} ({module.__name__})"
        )

    logger: Logger = logging.getLogger("modules")
    logger.info(f"Loaded the following module configurations:{module_overview}")

    return Injector(injector_modules)
