from isar.robot.robot import Robot
from isar.robot.robot_monitor_mission import RobotMonitorMissionThread
from isar.robot.robot_pause_mission import RobotPauseMissionThread
from isar.robot.robot_resume_mission import RobotResumeMissionThread
from isar.robot.robot_start_mission import RobotStartMissionThread
from isar.robot.robot_stop_mission import RobotStopMissionThread
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_mocks.pose import DummyPose


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
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=True)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        r_service.robot_service_events,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_thread_quitting,
        r_service.signal_mission_stopped,
        mission,
    )

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

    assert not r_service.signal_mission_stopped.is_set()
    assert r_service.monitor_mission_thread is not None

    assert not r_service.robot_service_events.mission_successfully_stopped.has_event()

    assert not r_service.signal_mission_stopped.is_set()


def test_stop_mission_waits_for_monitor_mission(
    mocked_robot_service: Robot, mocker
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStopMissionThread, "is_alive", return_value=False)
    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=True)
    mock_join_monitor_thread = mocker.patch(
        "isar.robot.robot.RobotMonitorMissionThread.join"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])

    r_service.monitor_mission_thread = RobotMonitorMissionThread(
        r_service.robot_service_events,
        r_service.robot,
        r_service.mqtt_publisher,
        r_service.signal_thread_quitting,
        r_service.signal_mission_stopped,
        mission,
    )

    r_service.stop_mission_thread = RobotStopMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )

    r_service._stop_mission_done_handler()

    assert not r_service.robot_service_events.mission_successfully_stopped.has_event()

    mocker.patch.object(RobotMonitorMissionThread, "is_alive", return_value=False)
    r_service._stop_mission_done_handler()

    assert r_service.robot_service_events.mission_successfully_stopped.has_event()
    mission_successfully_stopped_event = (
        r_service.robot_service_events.mission_successfully_stopped.get()
    )
    assert mission_successfully_stopped_event

    assert not r_service.robot_service_events.mission_failed_to_stop.has_event()
    assert not r_service.robot_service_events.mission_status_updated.has_event()

    assert r_service.signal_mission_stopped.is_set()
    mock_join_monitor_thread.assert_called_once()


def test_mission_succeeds_to_stop(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStopMissionThread, "is_alive", return_value=False)

    r_service.stop_mission_thread = RobotStopMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )

    r_service._stop_mission_done_handler()

    assert not r_service.robot_service_events.mission_failed_to_stop.has_event()
    assert r_service.robot_service_events.mission_successfully_stopped.has_event()

    assert not r_service.robot_service_events.mission_status_updated.has_event()

    assert r_service.monitor_mission_thread is None


def test_mission_fails_to_pause(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotPauseMissionThread, "is_alive", return_value=False)

    r_service.pause_mission_thread = RobotPauseMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )
    r_service.pause_mission_thread.error_message = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description="test"
    )

    r_service._pause_mission_done_handler()

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


def test_mission_succeeds_to_pause(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotPauseMissionThread, "is_alive", return_value=False)

    r_service.pause_mission_thread = RobotPauseMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )

    r_service._pause_mission_done_handler()

    assert not r_service.robot_service_events.mission_failed_to_pause.has_event()

    assert r_service.robot_service_events.mission_successfully_paused.has_event()


def test_mission_fails_to_resume(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotResumeMissionThread, "is_alive", return_value=False)

    r_service.resume_mission_thread = RobotResumeMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )
    r_service.resume_mission_thread.error_message = ErrorMessage(
        error_reason=ErrorReason.RobotUnknownErrorException, error_description="test"
    )

    r_service._resume_mission_done_handler()

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


def test_mission_succeeds_to_resume(mocked_robot_service: Robot, mocker) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotResumeMissionThread, "is_alive", return_value=False)

    r_service.resume_mission_thread = RobotResumeMissionThread(
        r_service.robot, r_service.signal_thread_quitting
    )

    r_service._resume_mission_done_handler()

    assert not r_service.robot_service_events.mission_failed_to_resume.has_event()

    assert r_service.robot_service_events.mission_successfully_resumed.has_event()


def test_mission_stop_waits_for_mission_to_start(
    mocked_robot_service: Robot, mocker
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStartMissionThread, "is_alive", return_value=True)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])
    r_service.start_mission_thread = RobotStartMissionThread(
        r_service.robot, r_service.signal_thread_quitting, mission
    )
    r_service.stop_mission_thread = None

    r_service.state_machine_events.stop_mission.trigger_event(True)

    r_service._stop_mission_request_handler(r_service.state_machine_events.stop_mission)

    assert r_service.state_machine_events.stop_mission.has_event()
    assert r_service.stop_mission_thread is None


def test_mission_stop_starts_when_start_is_done(
    mocked_robot_service: Robot, mocker
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStartMissionThread, "is_alive", return_value=False)

    mock_stop_mission_start = mocker.patch(
        "isar.robot.robot.RobotStopMissionThread.start"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])
    r_service.start_mission_thread = RobotStartMissionThread(
        r_service.robot, r_service.signal_thread_quitting, mission
    )
    r_service.stop_mission_thread = None

    r_service.state_machine_events.stop_mission.trigger_event(True)

    r_service._stop_mission_request_handler(r_service.state_machine_events.stop_mission)

    assert not r_service.state_machine_events.stop_mission.has_event()
    assert r_service.stop_mission_thread is not None
    mock_stop_mission_start.assert_called_once()


def test_mission_pause_waits_for_mission_to_start(
    mocked_robot_service: Robot, mocker
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStartMissionThread, "is_alive", return_value=True)

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])
    r_service.start_mission_thread = RobotStartMissionThread(
        r_service.robot, r_service.signal_thread_quitting, mission
    )
    r_service.pause_mission_thread = None

    r_service.state_machine_events.pause_mission.trigger_event(True)

    r_service._pause_mission_request_handler(
        r_service.state_machine_events.pause_mission
    )

    assert r_service.state_machine_events.pause_mission.has_event()
    assert r_service.pause_mission_thread is None


def test_mission_paus_starts_when_start_is_done(
    mocked_robot_service: Robot, mocker
) -> None:
    r_service = mocked_robot_service
    mocker.patch.object(RobotStartMissionThread, "is_alive", return_value=False)

    mock_pause_mission_start = mocker.patch(
        "isar.robot.robot.RobotPauseMissionThread.start"
    )

    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    mission: Mission = Mission(name="Dummy misson", tasks=[task_1])
    r_service.start_mission_thread = RobotStartMissionThread(
        r_service.robot, r_service.signal_thread_quitting, mission
    )
    r_service.pause_mission_thread = None

    r_service.state_machine_events.pause_mission.trigger_event(True)

    r_service._pause_mission_request_handler(
        r_service.state_machine_events.pause_mission
    )

    assert not r_service.state_machine_events.pause_mission.has_event()
    assert r_service.pause_mission_thread is not None
    mock_pause_mission_start.assert_called_once()
