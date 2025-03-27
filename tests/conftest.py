import pytest
from fastapi.testclient import TestClient

# from isar.apis.api import API
# from isar.config.keyvault.keyvault_service import Keyvault
# from isar.mission_planner.local_planner import LocalPlanner
# from isar.mission_planner.task_selector_interface import TaskSelectorInterface
# from isar.models.communication.queues.events import Events, SharedState
from isar.modules import ApplicationContainer

# from isar.services.service_connections.request_handler import RequestHandler
# from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states.idle import Idle
from isar.state_machine.states.monitor import Monitor

# from robot_interface.telemetry.mqtt_client import MqttClientInterface
from tests.mocks.robot_interface import MockRobot


@pytest.fixture()
def container():
    """Fixture to provide the dependency-injector container."""
    container = ApplicationContainer()
    container.config.from_dict(
        {
            "KEYVAULT_NAME": "test-keyvault",
            "MQTT_ENABLED": False,
            "TASK_SELECTOR": "sequential",
        }
    )
    return container


@pytest.fixture()
def app(container: ApplicationContainer):
    """Fixture to provide the FastAPI app."""
    app = container.api().get_app()
    return app


@pytest.fixture()
def client(app):
    """Fixture to provide a test client for the FastAPI app."""
    client = TestClient(app)
    return client


@pytest.fixture()
def access_token():
    """Fixture to provide a dummy access token."""
    return "DummyToken"


@pytest.fixture()
def keyvault(container: ApplicationContainer):
    """Fixture to provide the Keyvault instance."""
    return container.keyvault()


@pytest.fixture()
def state_machine(container: ApplicationContainer, robot):
    """Fixture to provide the StateMachine instance."""
    return StateMachine(
        events=container.events(),
        shared_state=container.shared_state(),
        robot=robot,
        mqtt_publisher=container.state_machine().mqtt_publisher,
        task_selector=container.task_selector(),
    )


@pytest.fixture()
def idle_state(state_machine):
    """Fixture to provide the Idle state."""
    return Idle(state_machine)


@pytest.fixture()
def monitor(state_machine):
    """Fixture to provide the Monitor state."""
    return Monitor(state_machine=state_machine)


@pytest.fixture()
def request_handler(container: ApplicationContainer):
    """Fixture to provide the RequestHandler instance."""
    return container.request_handler()


@pytest.fixture()
def local_planner(container: ApplicationContainer):
    """Fixture to provide the LocalPlanner instance."""
    return container.scheduling_utilities().mission_planner


@pytest.fixture()
def robot():
    """Fixture to provide a mock robot instance."""
    return MockRobot()


@pytest.fixture()
def scheduling_utilities(container: ApplicationContainer):
    """Fixture to provide the SchedulingUtilities instance."""
    return container.scheduling_utilities()


@pytest.fixture()
def mission_reader(container: ApplicationContainer):
    """Fixture to provide the LocalPlanner instance."""
    return container.scheduling_utilities().mission_planner
