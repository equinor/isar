from importlib import import_module
from types import ModuleType
from typing import List, Tuple

from injector import Module, multiprovider, provider, singleton

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
from isar.services.service_connections.mqtt.mqtt_client import (
    MqttClient,
    MqttClientInterface,
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
        return Keyvault(config.get("service_connections", "keyvault"))

    @provider
    @singleton
    def provide_stid_service(self, request_handler: RequestHandler) -> StidService:
        return StidService(request_handler=request_handler)


class MqttModule(Module):
    @provider
    @singleton
    def provide_mqtt_client(self) -> MqttClientInterface:
        mqtt_enabled: bool = config.getboolean("modules", "mqtt_enabled")
        if mqtt_enabled:
            return MqttClient()
        return None


modules: dict = {
    "api": {"default": APIModule},
    "authentication": {"default": AuthenticationModule},
    "queues": {"default": QueuesModule},
    "request_handler": {"default": RequestHandlerModule},
    "robot": {"default": RobotModule},
    "mission_planner": {
        "default": LocalPlannerModule,
        "local": LocalPlannerModule,
        "echo": EchoPlannerModule,
    },
    "service": {"default": ServiceModule},
    "state_machine": {"default": StateMachineModule},
    "storage": {
        "default": LocalStorageModule,
        "local": LocalStorageModule,
        "blob": BlobStorageModule,
        "slimm": SlimmStorageModule,
    },
    "mqtt_enabled": {
        "default": MqttModule,
        "false": MqttModule,
        "true": MqttModule,
    },
    "utilities": {"default": UtilitiesModule},
}


def get_injector_modules() -> Tuple[List[Module], List[str]]:
    injector_modules: List[Module] = []
    module_config_keys: List[str] = []

    module_config: dict = dict(config.items("modules"))

    for module_key, module in modules.items():
        if module_key not in module_config:
            injector_modules.append(module["default"])
            module_config_keys.append(f"{module_key} : default")

        else:
            config_list: List[str] = [
                x.strip() for x in module_config[module_key].split(",")
            ]

            for module_config_key in config_list:
                injector_modules.append(module[module_config_key])
                module_config_keys.append(f"{module_key} : {module_config_key}")

    return injector_modules, module_config_keys
