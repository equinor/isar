from isar.robot.robot import Robot
from isar.robot.robot_monitor_mission import RobotMonitorMissionThread
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_stop_mission import RobotStopMissionThread
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_double.pose import DummyPose


def test_mission_fails_to_schedule(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStartMissionThread, "is_alive", return_value=False)
    mock_publish_mission_status = mocker.patch(
        "isar.robot.robot.publish_mission_status"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.start_mission_thread = RobotStartMissionThread(
        r_service.robot, r_service.signal_thread_quitting, mission
    )
    r_service.start_mission_thread.error_message = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description="test"
    )

    r_service._start_mission_done_handler()

    assert r_service.robot_service_events.mission_failed.has_event()
    mission_failed_event = r_service.robot_service_events.mission_failed.get()
    assert mission_failed_event is not None
    assert mission_failed_event.error_reason == ErrorReason.RobotUnknownErrorException

    assert r_service.monitor_mission_thread is None

    mock_publish_mission_status.assert_called_once()


def test_mission_succeeds_to_schedule(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStartMissionThread, "is_alive", return_value=False)
    mock_publish_mission_status = mocker.patch(
        "isar.robot.robot.publish_mission_status"
    )
    mock_monitor_mission_start = mocker.patch(
        "isar.robot.robot.RobotMonitorMissionThread.start"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.signal_mission_stopped.set()  # We want to test that this is cleared

    r_service.start_mission_thread = RobotStartMissionThread(
        r_service.robot, r_service.signal_thread_quitting, mission
    )

    r_service._start_mission_done_handler()

    assert r_service.robot_service_events.mission_started.has_event()
    assert not r_service.signal_mission_stopped.is_set()
    assert r_service.monitor_mission_thread is not None
    assert r_service.monitor_mission_thread.current_mission.id == mission.id

    mock_publish_mission_status.assert_not_called()
    mock_monitor_mission_start.assert_called_once()


def test_mission_fails_to_stop(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStopMissionThread, "is_alive", return_value=False)

    r_service.stop_mission_thread = RobotStopMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )
    r_service.stop_mission_thread.error_message = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description="test"
    )

    r_service._stop_mission_done_handler()

    assert r_service.robot_service_events.mission_failed_to_stop.has_event()
    mission_failed_to_stop_event = (
        r_service.robot_service_events.mission_failed_to_stop.get()
    )
    assert mission_failed_to_stop_event is not None
    assert (
        mission_failed_to_stop_event.error_reason
        == ErrorReason.RobotUnknownErrorException
    )

    assert not r_service.robot_service_events.mission_successfully_stopped.has_event()

    assert not r_service.signal_mission_stopped.is_set()


def test_mission_succeeds_to_stop(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStopMissionThread, "is_alive", return_value=False)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.stop_mission_thread = RobotStopMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )
    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        r_service.robot_service_events,
        r_service.shared_state,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_thread_quitting,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service._stop_mission_done_handler()

    assert not r_service.robot_service_events.mission_failed_to_stop.has_event()
    assert r_service.robot_service_events.mission_successfully_stopped.has_event()

    assert r_service.signal_mission_stopped.is_set()

    assert r_service.monitor_mission_thread is None
