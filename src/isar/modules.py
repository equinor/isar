from importlib import import_module
from os import environ
from types import ModuleType

from injector import Module, provider, singleton

from isar.config import config
from isar.config.keyvault.keyvault_service import Keyvault
from isar.models.communication.queues.queues import Queues
from isar.models.map.map_config import MapConfig
from isar.services.coordinates.transformation import Transformation
from isar.services.readers.map_reader import MapConfigReader
from isar.services.readers.mission_reader import MissionReader
from isar.services.service_connections.echo.echo_service import (
    EchoService,
    EchoServiceInterface,
)
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.storage.blob_storage import BlobStorage
from isar.storage.storage_interface import StorageInterface
from isar.storage.storage_service import StorageService
from robot_interface.robot_interface import RobotInterface


class RobotModule(Module):
    @provider
    @singleton
    def provide_robot_interface(self) -> RobotInterface:
        robot_package_name: str = environ["ROBOT_DIRECTORY"]
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


class StorageModule(Module):
    @provider
    @singleton
    def provide_storage(self, keyvault: Keyvault) -> StorageInterface:
        return BlobStorage(keyvault)

    @provider
    @singleton
    def provide_storage_service(self, storage: StorageInterface) -> StorageService:
        return StorageService(storage=storage)


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
        return Keyvault(config.get("azure", "keyvault"))

    @provider
    @singleton
    def provide_stid_service(self, request_handler: RequestHandler) -> StidService:
        return StidService(request_handler=request_handler)

    @provider
    @singleton
    def provide_echo_service(
        self,
        request_handler: RequestHandler,
        stid_service: StidService,
        transform: Transformation,
    ) -> EchoServiceInterface:
        return EchoService(
            request_handler=request_handler,
            stid_service=stid_service,
            transform=transform,
        )


class ReaderModule(Module):
    @provider
    @singleton
    def provide_mission_reader(self) -> MissionReader:
        return MissionReader()

    @provider
    @singleton
    def provide_map_config_reader(self) -> MapConfigReader:
        return MapConfigReader()


class CoordinateModule(Module):
    @provider
    @singleton
    def provide_transform(self, map_config_reader: MapConfigReader) -> Transformation:
        map_config: MapConfig = map_config_reader.get_map_config_by_name(
            config.get("maps", "eq_robot_default_map_name")
        )
        return Transformation(map_config=map_config)
