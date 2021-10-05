from robot_interfaces.robot_scheduler_interface import RobotSchedulerInterface
from robot_interfaces.robot_storage_interface import RobotStorageInterface
from robot_interfaces.robot_telemetry_interface import RobotTelemetryInterface

from tests.test_utilities.mock_interface.mock_scheduler_interface import MockScheduler
from tests.test_utilities.mock_interface.mock_storage_interface import MockStorage
from tests.test_utilities.mock_interface.mock_telemetry_interface import MockTelemetry


def mock_default_interfaces(injector):
    mock_scheduler: MockScheduler = MockScheduler()
    injector.binder.bind(RobotSchedulerInterface, to=mock_scheduler)

    mock_storage: MockStorage = MockStorage()
    injector.binder.bind(RobotStorageInterface, to=mock_storage)

    mock_telemetry: MockTelemetry = MockTelemetry()
    injector.binder.bind(RobotTelemetryInterface, to=mock_telemetry)
