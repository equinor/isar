from injector import Module, provider, singleton
from isar.apis.schedule.drive_to import DriveTo
from isar.apis.schedule.start_mission import StartMission
from isar.apis.schedule.stop_mission import StopMission
from isar.apis.security.authentication import Authenticator
from isar.mission_planner.mission_planner_interface import MissionPlannerInterface
from isar.models.communication.queues.queues import Queues
from isar.services.utilities.scheduling_utilities import SchedulingUtilities

from isar.storage.storage_interface import StorageInterface
from robot_interface.robot_interface import RobotInterface
from tests.mocks.blob_storage import StorageMock
from tests.mocks.robot_interface import MockRobot


class MockStorageModule(Module):
    @provider
    @singleton
    def provide_storage(self) -> StorageInterface:
        return StorageMock()


class MockRobotModule(Module):
    @provider
    @singleton
    def provide_robot(self) -> RobotInterface:
        return MockRobot()


class MockNoAuthenticationModule(Module):
    @provider
    @singleton
    def provide_authenticator(self) -> Authenticator:
        return Authenticator(authentication_enabled=False)


class MockAuthenticationModule(Module):
    @provider
    @singleton
    def provide_authenticator(self) -> Authenticator:
        return Authenticator(authentication_enabled=True)
