import pytest
from fastapi.testclient import TestClient
from injector import Injector

from isar.app import create_app
from isar.config.keyvault.keyvault_service import Keyvault
from isar.mission_planner.echo_planner import EchoPlanner
from isar.mission_planner.local_planner import LocalPlanner
from isar.models.communication.queues.queues import Queues
from isar.modules import (
    APIModule,
    CoordinateModule,
    LocalPlannerModule,
    QueuesModule,
    ReaderModule,
    RequestHandlerModule,
    RobotModule,
    ServiceModule,
    StateMachineModule,
    UtilitiesModule,
)
from isar.services.coordinates.transformation import Transformation
from isar.services.readers.map_reader import MapConfigReader
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from isar.services.utilities.path_service import PathService
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states import Collect, Idle, Monitor, Send
from isar.storage.storage_service import StorageService
from tests.test_modules import MockStorageModule
from tests.test_utilities.mock_interface.mock_robot_interface import MockRobot


@pytest.fixture()
def injector():
    return Injector(
        [
            APIModule,
            CoordinateModule,
            QueuesModule,
            ReaderModule,
            RequestHandlerModule,
            RobotModule,
            ServiceModule,
            StateMachineModule,
            LocalPlannerModule,
            MockStorageModule,
            UtilitiesModule,
        ]
    )


@pytest.fixture()
def app(injector):
    app = create_app(injector=injector)
    return app


@pytest.fixture()
def client(app):
    client = TestClient(app)
    return client


@pytest.fixture()
def access_token():
    return "DummyToken"


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def path_service():
    return PathService()


@pytest.fixture()
def keyvault(injector):
    return injector.get(Keyvault)


@pytest.fixture()
def state_machine(injector, robot, transform):
    return StateMachine(
        queues=injector.get(Queues),
        robot=robot,
        transform=transform,
        storage_service=injector.get(StorageService),
    )


@pytest.fixture()
def idle_state(state_machine):
    return Idle(state_machine)


@pytest.fixture()
def send(state_machine):
    return Send(state_machine)


@pytest.fixture()
def monitor(state_machine):
    return Monitor(state_machine)


@pytest.fixture()
def collect(state_machine, injector):
    return Collect(state_machine, injector.get(Transformation))


@pytest.fixture()
def request_handler(injector):
    return injector.get(RequestHandler)


@pytest.fixture()
def stid_service(injector):
    return injector.get(StidService)


@pytest.fixture()
def echo_service(injector):
    return injector.get(EchoPlanner)


@pytest.fixture()
def local_planner(injector):
    return injector.get(LocalPlanner)


@pytest.fixture()
def robot():
    return MockRobot()


@pytest.fixture()
def scheduling_utilities(app, injector):
    return injector.get(SchedulingUtilities)


@pytest.fixture()
def mission_reader(injector):
    return injector.get(LocalPlanner)


@pytest.fixture()
def map_config_reader(injector):
    return injector.get(MapConfigReader)


@pytest.fixture()
def transform(injector):
    return injector.get(Transformation)
