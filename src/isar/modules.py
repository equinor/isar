from importlib import import_module
from types import ModuleType
from typing import List, Tuple

from injector import Module, provider, singleton

from isar.apis.api import API
from isar.apis.schedule.drive_to import DriveTo
from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission
from isar.apis.security.authentication import Authenticator
from isar.config import config
from isar.config.keyvault.keyvault_service import Keyvault
from isar.mission_planner.echo_planner import EchoPlanner
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.mission_planner_interface import MissionPlannerInterface
from isar.models.communication.queues.queues import Queues
from isar.models.map.map_config import MapConfig
from isar.services.coordinates.transformation import Transformation
from isar.services.readers.map_reader import MapConfigReader
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.storage.blob_storage import BlobStorage
from isar.storage.local_storage import LocalStorage
from isar.storage.storage_interface import StorageInterface
from isar.storage.storage_service import StorageService
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
        robot_package_name: str = config.get("DEFAULT", "robot_package")
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
    @provider
    @singleton
    def provide_blob_storage(self, keyvault: Keyvault) -> StorageInterface:
        return BlobStorage(keyvault)


class LocalStorageModule(Module):
    @provider
    @singleton
    def provide_local_storage(self) -> StorageInterface:
        return LocalStorage()


class StorageServiceModule(Module):
    @provider
    @singleton
    def provide_storage_service(self, storage: StorageInterface) -> StorageService:
        return StorageService(storage=storage)


class LocalPlannerModule(Module):
    @provider
    @singleton
    def provide_local_planner(
        self, transform: Transformation
    ) -> MissionPlannerInterface:
        return LocalPlanner(transform=transform)


class EchoPlannerModule(Module):
    @provider
    @singleton
    def provide_echo_planner(
        self,
        request_handler: RequestHandler,
        stid_service: StidService,
        transform: Transformation,
    ) -> MissionPlannerInterface:
        return EchoPlanner(
            request_handler=request_handler,
            stid_service=stid_service,
            transform=transform,
        )


class StateMachineModule(Module):
    @provider
    @singleton
    def provide_state_machine(
        self,
        queues: Queues,
        robot: RobotInterface,
        storage_service: StorageService,
        transform: Transformation,
    ) -> StateMachine:
        return StateMachine(
            queues=queues,
            robot=robot,
            storage_service=storage_service,
            transform=transform,
        )


class UtilitiesModule(Module):
    @provider
    @singleton
    def provide_scheduling_utilities(self, queues: Queues) -> SchedulingUtilities:
        return SchedulingUtilities(queues)


class ServiceModule(Module):
    @provider
    @singleton
    def provide_keyvault(self) -> Keyvault:
        return Keyvault(config.get("service_connections", "keyvault"))

    @provider
    @singleton
    def provide_stid_service(self, request_handler: RequestHandler) -> StidService:
        return StidService(request_handler=request_handler)


class ReaderModule(Module):
    @provider
    @singleton
    def provide_map_config_reader(self) -> MapConfigReader:
        return MapConfigReader()


class CoordinateModule(Module):
    @provider
    @singleton
    def provide_transform(self, map_config_reader: MapConfigReader) -> Transformation:
        map_config: MapConfig = map_config_reader.get_map_config_by_name(
            config.get("DEFAULT", "default_map")
        )
        return Transformation(map_config=map_config)


modules: dict = {
    "api": {"default": APIModule},
    "authentication": {"default": AuthenticationModule},
    "coordinate": {"default": CoordinateModule},
    "queues": {"default": QueuesModule},
    "reader": {"default": ReaderModule},
    "request_handler": {"default": RequestHandlerModule},
    "robot": {"default": RobotModule},
    "mission_planner": {
        "default": LocalPlannerModule,
        "local": LocalPlannerModule,
        "echo": EchoPlannerModule,
    },
    "service": {"default": ServiceModule},
    "state_machine": {"default": StateMachineModule},
    "storage_service": {"default": StorageServiceModule},
    "storage": {
        "default": LocalStorageModule,
        "local": LocalStorageModule,
        "blob": BlobStorageModule,
    },
    "utilities": {"default": UtilitiesModule},
}


def get_injector_modules() -> Tuple[List[Module], List[str]]:
    injector_modules: List[Module] = []
    module_config_keys: List[str] = []

    module_config: dict = dict(config.items("modules"))

    for module_key, module in modules.items():

        module_config_key = (
            "default" if not module_key in module_config else module_config[module_key]
        )

        injector_modules.append(module[module_config_key])
        module_config_keys.append(f"{module_key} : {module_config_key}")

    return injector_modules, module_config_keys
