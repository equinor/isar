from pytest_mock import MockerFixture

from isar.robot.function_thread import FunctionThread
from isar.robot.robot import Robot
from isar.robot.robot_monitor_mission import RobotMonitorMissionThread
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotAlreadyHomeException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_mocks.pose import DummyPose


def test_mission_fails_to_schedule(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(FunctionThread, "is_alive", return_value=False)
    mock_publish_mission_status = mocker.patch(
        "isar.robot.robot.publish_mission_status"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    mocker.patch(
        "isar.robot.robot.robot_start_mission",
        return_value=ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        ),
    )

    r_service._start_mission_handler(mission)

    assert r_service.robot_service_events.mission_failed.has_event()
    mission_failed_event = r_service.robot_service_events.mission_failed.get()
    assert mission_failed_event is not None
    assert mission_failed_event.error_reason == ErrorReason.RobotUnknownErrorException

    assert r_service.monitor_mission_thread is None

    assert mock_publish_mission_status.call_count == 2


def test_mission_succeeds_to_schedule(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service
    mock_publish_mission_status = mocker.patch(
        "isar.robot.robot.publish_mission_status"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.signal_mission_stopped.set()  # We want to test that this is cleared

    mocker.patch("isar.robot.robot.robot_start_mission", return_value=None)

    r_service._start_mission_handler(mission)

    assert not r_service.signal_mission_stopped.is_set()
    mission_started_event = (
        r_service.robot_service_events.mission_started.consume_event()
    )
    assert mission_started_event is not None
    assert mission_started_event.id == mission.id

    mock_publish_mission_status.assert_called_once()


def test_mission_fails_to_stop(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        lambda task: None,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_exit,
        r_service.signal_mission_stopped,
        mission,
    )

    mocker.patch(
        "isar.robot.robot.robot_stop_mission",
        return_value=ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        ),
    )

    r_service._stop_mission_handler()

    assert r_service.robot_service_events.mission_failed_to_stop.has_event()
    mission_failed_to_stop_event = (
        r_service.robot_service_events.mission_failed_to_stop.get()
    )
    assert mission_failed_to_stop_event is not None
    assert (
        mission_failed_to_stop_event.error_reason
        == ErrorReason.RobotUnknownErrorException
    )
    assert not r_service.signal_mission_stopped.is_set()
    assert r_service.monitor_mission_thread is not None
    assert not r_service.robot_service_events.mission_successfully_stopped.has_event()


def test_successful_stop(mocked_robot_service: Robot, mocker: MockerFixture) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=True)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])
    mocker.patch("isar.robot.robot.robot_stop_mission", return_value=None)

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        lambda task: None,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_exit,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service._stop_mission_handler()

    assert r_service.robot_service_events.mission_successfully_stopped.has_event()
    assert r_service.signal_mission_stopped.is_set()
    assert not r_service.robot_service_events.mission_failed_to_stop.has_event()
    assert not r_service.robot_service_events.mission_failed.has_event()
    assert not r_service.robot_service_events.mission_succeeded.has_event()


def test_monitor_mission_handler_waits_for_thread(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=True)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        lambda task: None,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_exit,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service.signal_mission_stopped.set()

    r_service._monitor_mission_done_handler()

    assert r_service.monitor_mission_thread is not None


def test_monitor_mission_reports_nothing_after_mission_stopped(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=False)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        lambda task: None,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_exit,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service.signal_mission_stopped.set()

    r_service._monitor_mission_done_handler()

    assert not r_service.robot_service_events.mission_succeeded.has_event()
    assert not r_service.robot_service_events.mission_failed.has_event()

    assert r_service.monitor_mission_thread is None


def test_monitor_mission_reports_mission_failed(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=False)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        lambda task: None,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_exit,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service.monitor_mission_thread.error_message = ErrorMessage(
        ErrorReason.RobotUnknownErrorException, ""
    )

    r_service._monitor_mission_done_handler()

    assert not r_service.robot_service_events.mission_succeeded.has_event()
    assert r_service.robot_service_events.mission_failed.has_event()

    assert r_service.monitor_mission_thread is None


def test_monitor_mission_reports_mission_success(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=False)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        lambda task: None,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_exit,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service._monitor_mission_done_handler()

    assert r_service.robot_service_events.mission_succeeded.has_event()
    assert not r_service.robot_service_events.mission_failed.has_event()

    assert r_service.monitor_mission_thread is None


def test_mission_fails_to_pause(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service

    mocker.patch(
        "isar.robot.robot.robot_pause_mission",
        return_value=ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        ),
    )

    r_service._pause_mission_handler()

    assert r_service.robot_service_events.mission_failed_to_pause.has_event()
    mission_failed_to_pause_event = (
        r_service.robot_service_events.mission_failed_to_pause.get()
    )
    assert mission_failed_to_pause_event is not None
    assert (
        mission_failed_to_pause_event.error_reason
        == ErrorReason.RobotUnknownErrorException
    )

    assert not r_service.robot_service_events.mission_successfully_paused.has_event()


def test_mission_succeeds_to_pause(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service

    mocker.patch("isar.robot.robot.robot_pause_mission", return_value=None)

    r_service._pause_mission_handler()

    assert not r_service.robot_service_events.mission_failed_to_pause.has_event()
    assert r_service.robot_service_events.mission_successfully_paused.has_event()


def test_mission_fails_to_resume(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service

    mocker.patch(
        "isar.robot.robot.robot_resume_mission",
        return_value=ErrorMessage(
            error_reason=ErrorReason.RobotUnknownErrorException,
            error_description="test",
        ),
    )

    r_service._resume_mission_handler()

    assert r_service.robot_service_events.mission_failed_to_resume.has_event()
    mission_failed_to_resume_event = (
        r_service.robot_service_events.mission_failed_to_resume.get()
    )
    assert mission_failed_to_resume_event is not None
    assert (
        mission_failed_to_resume_event.error_reason
        == ErrorReason.RobotUnknownErrorException
    )

    assert not r_service.robot_service_events.mission_successfully_resumed.has_event()


def test_mission_succeeds_to_resume(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service

    mocker.patch("isar.robot.robot.robot_resume_mission", return_value=None)

    r_service._resume_mission_handler()

    assert not r_service.robot_service_events.mission_failed_to_resume.has_event()
    assert r_service.robot_service_events.mission_successfully_resumed.has_event()


def test_start_mission_reports_robot_already_home(
    mocked_robot_service: Robot, mocker: MockerFixture
) -> None:
    r_service = mocked_robot_service

    def mock_initiate_mission(mission: Mission) -> None:
        raise RobotAlreadyHomeException("test")

    r_service.robot.initiate_mission = mock_initiate_mission  # type: ignore

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy mission", tasks=[task_1])
    r_service._start_mission_handler(mission)

    assert r_service.robot_service_events.robot_already_home.has_event()
    assert not r_service.robot_service_events.mission_started.has_event()
    assert r_service.monitor_mission_thread is None
