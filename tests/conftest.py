import pytest
from azure.identity import DefaultAzureCredential
from injector import Injector

from isar import create_app
from isar.config import config
from isar.config.keyvault.keyvault_service import Keyvault
from isar.models.communication.queues.queues import Queues
from isar.modules import (
    CoordinateModule,
    QueuesModule,
    ReaderModule,
    RequestHandlerModule,
    RobotModule,
    SchedulerModule,
    ServiceModule,
    StateMachineModule,
    StorageModule,
    TelemetryModule,
    UtilitiesModule,
)
from isar.services.coordinates.transformation import Transformation
from isar.services.readers.map_reader import MapConfigReader
from isar.services.readers.mission_reader import MissionReader
from isar.services.service_connections.azure.blob_service import BlobService
from isar.services.service_connections.echo.echo_service import EchoServiceInterface
from isar.services.service_connections.request_handler import RequestHandler
from isar.services.service_connections.slimm.slimm_service import SlimmService
from isar.services.service_connections.stid.stid_service import StidService
from isar.services.utilities.path_service import PathService
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states import Cancel, Collect, Idle, Monitor, Send
from tests.test_utilities.mock_interface.mock_scheduler_interface import MockScheduler
from tests.test_utilities.mock_interface.mock_storage_interface import MockStorage
from tests.test_utilities.mock_interface.mock_telemetry_interface import MockTelemetry


@pytest.fixture()
def injector():
    return Injector(
        [
            TelemetryModule,
            QueuesModule,
            StateMachineModule,
            StorageModule,
            SchedulerModule,
            ServiceModule,
            UtilitiesModule,
            RobotModule,
            ReaderModule,
            RequestHandlerModule,
            CoordinateModule,
        ]
    )


@pytest.fixture()
def app():
    app = create_app(test_config=True)
    with app.app_context():
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def azure_credential():
    return DefaultAzureCredential()


@pytest.fixture()
def access_token(azure_credential):
    return azure_credential.get_token(
        "api://b29bed99-7637-4fdc-8809-48c777a9b714/.default"
    ).token


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def blob_service(keyvault):
    test_container_name: str = config.get("test", "test_azure_container_name")
    return BlobService(keyvault=keyvault, container_name=test_container_name)


@pytest.fixture()
def path_service():
    return PathService()


@pytest.fixture()
def keyvault(injector):
    return injector.get(Keyvault)


@pytest.fixture()
def state_machine(injector, scheduler_interface, storage_interface, transform):
    return StateMachine(
        queues=injector.get(Queues),
        scheduler=scheduler_interface,
        storage=storage_interface,
        transform=transform,
        slimm_service=injector.get(SlimmService),
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
    return Collect(state_machine, MockStorage(), injector.get(Transformation))


@pytest.fixture()
def request_handler(injector):
    return injector.get(RequestHandler)


@pytest.fixture()
def stid_service(injector):
    return injector.get(StidService)


@pytest.fixture()
def echo_service(injector):
    return injector.get(EchoServiceInterface)


@pytest.fixture()
def cancel(state_machine):
    return Cancel(state_machine, MockStorage())


@pytest.fixture()
def scheduler_interface():
    return MockScheduler()


@pytest.fixture()
def telemetry_interface():
    return MockTelemetry()


@pytest.fixture()
def storage_interface():
    return MockStorage()


@pytest.fixture()
def scheduling_utilities(app, injector):
    return injector.get(SchedulingUtilities)


@pytest.fixture()
def mission_reader(injector):
    return injector.get(MissionReader)


@pytest.fixture()
def map_config_reader(injector):
    return injector.get(MapConfigReader)


@pytest.fixture()
def transform(injector):
    return injector.get(Transformation)
