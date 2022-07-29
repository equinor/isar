import pytest
from fastapi.routing import APIRouter
from fastapi.testclient import TestClient
from injector import Injector

from isar.apis.api import API
from isar.config.keyvault.keyvault_service import Keyvault
from isar.mission_planner.echo_planner import EchoPlanner
from isar.mission_planner.local_planner import LocalPlanner
from isar.mission_planner.task_selector_interface import TaskSelectorInterface
from isar.models.communication.queues.queues import Queues
from isar.modules import (
    APIModule,
    LocalPlannerModule,
    QueuesModule,
    RequestHandlerModule,
    SequentialTaskSelectorModule,
    ServiceModule,
    StateMachineModule,
    UtilitiesModule,
)
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.stid.stid_service import StidService
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states import Idle, InitiateStep, Monitor
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from tests.mocks.robot_interface import MockRobot
from tests.test_modules import (
    MockAuthenticationModule,
    MockMqttModule,
    MockNoAuthenticationModule,
    MockRobotModule,
    MockStorageModule,
)


@pytest.fixture()
def injector():
    return Injector(
        [
            APIModule,
            LocalPlannerModule,
            MockMqttModule,
            MockNoAuthenticationModule,
            MockRobotModule,
            MockStorageModule,
            QueuesModule,
            RequestHandlerModule,
            ServiceModule,
            StateMachineModule,
            SequentialTaskSelectorModule,
            UtilitiesModule,
        ]
    )


@pytest.fixture()
def injector_auth():
    return Injector(
        [
            APIModule,
            LocalPlannerModule,
            MockAuthenticationModule,
            MockMqttModule,
            MockRobotModule,
            MockStorageModule,
            QueuesModule,
            RequestHandlerModule,
            ServiceModule,
            StateMachineModule,
            UtilitiesModule,
        ]
    )


@pytest.fixture()
def app(injector):
    app = injector.get(API).get_app()
    return app


@pytest.fixture()
def api_router():
    return APIRouter


@pytest.fixture()
def client(app):
    client = TestClient(app)
    return client


@pytest.fixture()
def client_auth(injector_auth):
    app = injector_auth.get(API).get_app()
    client_auth = TestClient(app)
    return client_auth


@pytest.fixture()
def access_token():
    return "DummyToken"


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def keyvault(injector):
    return injector.get(Keyvault)


@pytest.fixture()
def state_machine(injector, robot):
    return StateMachine(
        queues=injector.get(Queues),
        robot=robot,
        mqtt_publisher=injector.get(MqttClientInterface),
        task_selector=injector.get(TaskSelectorInterface),
    )


@pytest.fixture()
def idle_state(state_machine):
    return Idle(state_machine)


@pytest.fixture()
def initiate_step(state_machine):
    return InitiateStep(state_machine)


@pytest.fixture()
def monitor(state_machine):
    return Monitor(state_machine=state_machine)


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
