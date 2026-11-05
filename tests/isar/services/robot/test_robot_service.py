import asyncio

import pytest
from pytest_mock import MockerFixture

from isar.models.events import EmptyMessage
from isar.robot.robot_service import RobotService
from robot_interface.models.exceptions.robot_exceptions import (
    ErrorMessage,
    ErrorReason,
    RobotAlreadyHomeException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import TaskStatus


def test_mission_fails_to_schedule(
    mocked_robot_service: RobotService, mission: Mission, mocker: MockerFixture
) -> None:
    mocker.patch(
        "isar.robot.robot_service.robot_start_mission",
        return_value=ErrorMessage(ErrorReason.RobotUnknownErrorException, "test"),
    )

    success = mocked_robot_service._start_mission_handler(mission)

    assert not success
    assert (
        mocked_robot_service.action_requests.execute_mission.failure.consume_event()
        == ErrorMessage(
            ErrorReason.RobotUnknownErrorException, "Failed to initiate due to: test"
        )
    )


def test_mission_succeeds_to_schedule(
    mocked_robot_service: RobotService, mission: Mission, mocker: MockerFixture
) -> None:
    mocker.patch("isar.robot.robot_service.robot_start_mission", return_value=None)

    success = mocked_robot_service._start_mission_handler(mission)

    assert success


def test_mission_fails_to_stop(
    mocked_robot_service: RobotService, mocker: MockerFixture
) -> None:
    mocker.patch(
        "isar.robot.robot_service.robot_stop_mission",
        return_value=ErrorMessage(ErrorReason.RobotUnknownErrorException, "test"),
    )
    response = mocked_robot_service.action_requests.stop_mission

    asyncio.run(mocked_robot_service._stop_mission_handler(None))

    assert isinstance(response.failure.consume_event(), EmptyMessage)
    assert not response.success.has_event()


@pytest.mark.parametrize(
    "task_status",
    [
        pytest.param(TaskStatus.Cancelled, id="remaining-tasks"),
        pytest.param(TaskStatus.Successful, id="completed-tasks"),
        pytest.param(None, id="no-monitor"),
    ],
)
def test_successful_stop_returns_remaining_work_without_completing_mission(
    mocked_robot_service: RobotService,
    mission: Mission,
    mocker: MockerFixture,
    task_status: TaskStatus | None,
) -> None:
    service = mocked_robot_service
    mocker.patch("isar.robot.robot_service.robot_stop_mission", return_value=None)
    if task_status is not None:
        mission.tasks[0].status = task_status
    mocker.patch(
        "isar.robot.robot_service.robot_monitor_mission",
        return_value=(None, mission, True),
    )

    async def stop_mission() -> None:
        monitor = None
        if task_status is not None:
            monitor = asyncio.create_task(service._monitor_mission_handler(mission))
            await asyncio.sleep(0)
        await service._stop_mission_handler(monitor)

    asyncio.run(stop_mission())

    response = service.action_requests.stop_mission.success.consume_event()
    if task_status == TaskStatus.Cancelled:
        assert response == mission
    else:
        assert isinstance(response, EmptyMessage)
    assert not service.action_requests.stop_mission.failure.has_event()
    assert (
        service.action_requests.execute_mission.success.consume_event(),
        service.action_requests.execute_mission.failure.consume_event(),
    ) == (None, None)


def test_monitor_mission_reports_nothing_after_mission_stopped(
    mocked_robot_service: RobotService, mission: Mission, mocker: MockerFixture
) -> None:
    mocker.patch(
        "isar.robot.robot_service.robot_monitor_mission",
        side_effect=asyncio.CancelledError(),
    )
    response = mocked_robot_service.action_requests.execute_mission

    asyncio.run(mocked_robot_service._monitor_mission_handler(mission))

    assert not response.failure.has_event()
    assert not response.success.has_event()


@pytest.mark.parametrize("failed", [False, True], ids=["success", "failure"])
def test_monitor_mission_reports_outcome(
    mocked_robot_service: RobotService,
    mission: Mission,
    mocker: MockerFixture,
    failed: bool,
) -> None:
    error = ErrorMessage(ErrorReason.RobotUnknownErrorException, "test")
    mocker.patch(
        "isar.robot.robot_service.robot_monitor_mission",
        return_value=(error if failed else None, None, False),
    )
    response = mocked_robot_service.action_requests.execute_mission

    asyncio.run(mocked_robot_service._monitor_mission_handler(mission))

    assert response.success.has_event() is not failed
    assert response.failure.consume_event() == (error if failed else None)


@pytest.mark.parametrize("action", ["pause", "resume"])
@pytest.mark.parametrize("failed", [False, True], ids=["success", "failure"])
def test_mission_control_reports_outcome(
    mocked_robot_service: RobotService,
    mocker: MockerFixture,
    action: str,
    failed: bool,
) -> None:
    mocker.patch(
        f"isar.robot.robot_service.robot_{action}_mission",
        return_value=(
            ErrorMessage(ErrorReason.RobotUnknownErrorException, "test")
            if failed
            else None
        ),
    )
    handler = getattr(mocked_robot_service, f"_{action}_mission_handler")
    response = getattr(mocked_robot_service.action_requests, f"{action}_mission")
    expected_event = response.failure if failed else response.success
    unexpected_event = response.success if failed else response.failure

    handler()

    assert isinstance(expected_event.consume_event(), EmptyMessage)
    assert not unexpected_event.has_event()


def test_start_mission_reports_robot_already_home(
    mocked_robot_service: RobotService, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        mocked_robot_service.robot,
        "initiate_return_home",
        side_effect=RobotAlreadyHomeException("test"),
    )

    success = mocked_robot_service._start_return_home_handler("id")

    assert not success
    assert mocked_robot_service.action_requests.return_home.success.has_event()
