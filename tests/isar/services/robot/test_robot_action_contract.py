import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events, RobotActionEvent
from isar.robot.robot_service import RobotService
from robot_interface.models.exceptions.robot_exceptions import (
    RobotActionException,
    RobotAlreadyHomeException,
    RobotNoMissionRunningException,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.polygon import Polygon
from robot_interface.models.mission.status import MissionStatus, TaskStatus
from tests.test_mocks.robot_interface import StubRobot


class MockRobotInterface(StubRobot):

    def __init__(self) -> None:
        super().__init__()
        self.initiate_mission_behavior: Callable[[Mission], None] = lambda _: None
        self.initiate_return_home_behavior: Callable[[str], None] = lambda _: None
        self.stop_behavior: Callable[[], None] = lambda: None
        self.pause_behavior: Callable[[], None] = lambda: None
        self.resume_behavior: Callable[[], None] = lambda: None
        self.mission_status_behavior: Callable[[str], MissionStatus] = (
            lambda _: MissionStatus.Successful
        )
        self.task_status_behavior: Callable[[str], TaskStatus] = (
            lambda _: TaskStatus.Successful
        )
        self.update_exclusion_polygons_behavior: Callable[[Any], None] = lambda _: None

    def initiate_mission(self, mission: Mission) -> None:
        self.initiate_mission_behavior(mission)

    def initiate_return_home(self, mission_id: str) -> None:
        self.initiate_return_home_behavior(mission_id)

    def stop(self) -> None:
        self.stop_behavior()

    def pause(self) -> None:
        self.pause_behavior()

    def resume(self) -> None:
        self.resume_behavior()

    def mission_status(self, mission_id: str) -> MissionStatus:
        return self.mission_status_behavior(mission_id)

    def task_status(self, task_id: str) -> TaskStatus:
        return self.task_status_behavior(task_id)

    def update_exclusion_polygons(self, polygons: list[Polygon]) -> None:
        return self.update_exclusion_polygons_behavior(polygons)


async def _wait_for_response(
    action: RobotActionEvent[Any, Any, Any],
    loop_task: asyncio.Task[None],
    timeout: float = 1.0,
) -> tuple[bool, bool]:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if loop_task.done():
            loop_task.result()
            raise AssertionError("RobotService event loop exited unexpectedly")
        has_success = action.success.has_event()
        has_failure = action.failure.has_event()
        if has_success or has_failure:
            return has_success, has_failure
        await asyncio.sleep(0.005)
    raise AssertionError(f"Timed out waiting for response to {action.request.name}")


def _raise(exc: Exception) -> Callable[..., None]:
    def _raiser(*_: Any, **__: Any) -> None:
        raise exc

    return _raiser


ACTION_OUTCOMES: list[tuple[str, str, str, Callable[[MockRobotInterface], None]]] = [
    ("execute_mission", "success", "success", lambda _: None),
    (
        "execute_mission",
        "robot_exception",
        "failure",
        lambda r: setattr(
            r,
            "initiate_mission_behavior",
            _raise(RobotActionException("initiate failed")),
        ),
    ),
    (
        "execute_mission",
        "monitor_failed",
        "failure",
        lambda r: setattr(
            r,
            "mission_status_behavior",
            lambda _: MissionStatus.Failed,
        ),
    ),
    ("return_home", "success", "success", lambda _: None),
    (
        "return_home",
        "already_home",
        "success",
        lambda r: setattr(
            r,
            "initiate_return_home_behavior",
            _raise(RobotAlreadyHomeException("already home")),
        ),
    ),
    (
        "return_home",
        "robot_exception",
        "failure",
        lambda r: setattr(
            r,
            "initiate_return_home_behavior",
            _raise(RobotActionException("return home failed")),
        ),
    ),
    (
        "return_home",
        "monitor_failed",
        "failure",
        lambda r: setattr(
            r,
            "mission_status_behavior",
            lambda _: MissionStatus.Failed,
        ),
    ),
    ("pause_mission", "success", "success", lambda _: None),
    (
        "pause_mission",
        "no_mission_running",
        "failure",
        lambda r: setattr(
            r,
            "pause_behavior",
            _raise(RobotNoMissionRunningException("no mission")),
        ),
    ),
    (
        "pause_mission",
        "robot_exception",
        "failure",
        lambda r: setattr(
            r,
            "pause_behavior",
            _raise(RobotActionException("pause failed")),
        ),
    ),
    ("resume_mission", "success", "success", lambda _: None),
    (
        "resume_mission",
        "no_mission_running",
        "failure",
        lambda r: setattr(
            r,
            "resume_behavior",
            _raise(RobotNoMissionRunningException("no mission")),
        ),
    ),
    (
        "resume_mission",
        "robot_exception",
        "failure",
        lambda r: setattr(
            r,
            "resume_behavior",
            _raise(RobotActionException("resume failed")),
        ),
    ),
    ("stop_mission", "success", "success", lambda _: None),
    (
        "stop_mission",
        "no_mission_running",
        "success",
        lambda r: setattr(
            r,
            "stop_behavior",
            _raise(RobotNoMissionRunningException("no mission")),
        ),
    ),
    (
        "stop_mission",
        "robot_exception",
        "failure",
        lambda r: setattr(
            r,
            "stop_behavior",
            _raise(RobotActionException("stop failed")),
        ),
    ),
    (
        "update_exclusion_polygons",
        "robot_exception",
        "failure",
        lambda r: setattr(
            r,
            "update_exclusion_polygons_behavior",
            _raise(RobotActionException("update exclusion polygons failed")),
        ),
    ),
    ("update_exclusion_polygons", "success", "success", lambda _: None),
]


def test_action_contract_cases_covers_all_robot_action_requests(
    events: Events,
) -> None:
    declared_actions = {
        name
        for name, value in vars(events.action_requests).items()
        if isinstance(value, RobotActionEvent)
    }
    tested_actions = {action_name for action_name, _, _, _ in ACTION_OUTCOMES}
    assert tested_actions == declared_actions


ALL_CASES = [
    (precondition, action_name, outcome_name, expected_channel, configure_robot)
    for precondition in ("idle", "monitoring_mission", "monitoring_return_home")
    for action_name, outcome_name, expected_channel, configure_robot in ACTION_OUTCOMES
    if (
        precondition == "idle"
        or action_name
        not in ("execute_mission", "return_home", "update_exclusion_polygons")
    )
    and (precondition != "idle" or action_name != "stop_mission")
]


@pytest.mark.parametrize(
    (
        "precondition",
        "action_name",
        "outcome_name",
        "expected_channel",
        "configure_robot",
    ),
    ALL_CASES,
    ids=[f"{pre}-{action}-{outcome}" for pre, action, outcome, _, _ in ALL_CASES],
)
def test_robot_action_request_always_receives_single_response(
    events: Events,
    mission: Mission,
    monkeypatch: pytest.MonkeyPatch,
    precondition: str,
    action_name: str,
    outcome_name: str,
    expected_channel: str,
    configure_robot: Callable[[MockRobotInterface], None],
) -> None:
    monkeypatch.setattr(settings, "FSM_SLEEP_TIME", 0.0)
    monkeypatch.setattr(settings, "ROBOT_REQUEST_ATTEMPTS_LIMIT", 1)

    robot = MockRobotInterface()
    service = RobotService(events, robot, events.mqtt_queue)
    action: RobotActionEvent[Any, Any, Any] = getattr(
        events.action_requests, action_name
    )

    async def simulate_request_response_loop() -> tuple[bool, bool]:
        loop_task = asyncio.create_task(service._run_main_event_loop())
        try:
            if precondition != "idle":
                robot.mission_status_behavior = lambda _: MissionStatus.InProgress
                robot.task_status_behavior = lambda _: TaskStatus.InProgress
                if precondition == "monitoring_mission":
                    events.action_requests.execute_mission.trigger_request(mission)
                else:
                    events.action_requests.return_home.trigger_request(EmptyMessage())
                # Let the main loop consume the start request and spawn the monitor task
                await asyncio.sleep(0.02)

            configure_robot(robot)
            action.trigger_request(
                mission if action_name == "execute_mission" else EmptyMessage()
            )
            return await _wait_for_response(action, loop_task)
        finally:
            service.signal_exit.set()
            await loop_task

    has_success, has_failure = asyncio.run(simulate_request_response_loop())
    assert has_success ^ has_failure, (
        f"{action_name} ({outcome_name}, precondition={precondition}) "
        f"produced success={has_success}, failure={has_failure}"
    )
    assert has_success if expected_channel == "success" else has_failure


@pytest.mark.parametrize("running_action", ["execute_mission", "return_home"])
def test_stop_mission_replaces_monitor_request_without_outputting_monitor_response(
    events: Events,
    mission: Mission,
    monkeypatch: pytest.MonkeyPatch,
    running_action: str,
) -> None:
    monkeypatch.setattr(settings, "FSM_SLEEP_TIME", 0.0)
    monkeypatch.setattr(settings, "ROBOT_REQUEST_ATTEMPTS_LIMIT", 1)

    robot = MockRobotInterface()
    robot.mission_status_behavior = lambda _: MissionStatus.InProgress
    robot.task_status_behavior = lambda _: TaskStatus.InProgress
    service = RobotService(events, robot, events.mqtt_queue)

    monitor_mission_request: RobotActionEvent[Any, Any, Any] = getattr(
        events.action_requests, running_action
    )
    stop_action = events.action_requests.stop_mission

    async def simulate_request_response_loop() -> None:
        loop_task = asyncio.create_task(service._run_main_event_loop())
        try:
            payload: Any = (
                mission if running_action == "execute_mission" else EmptyMessage()
            )
            monitor_mission_request.trigger_request(payload)
            for _ in range(50):
                if not monitor_mission_request.request.has_event():
                    break
                await asyncio.sleep(0.005)
            await asyncio.sleep(0.02)

            stop_action.trigger_request(EmptyMessage())
            has_success, has_failure = await _wait_for_response(stop_action, loop_task)
            assert has_success and not has_failure
            await asyncio.sleep(0.02)
        finally:
            service.signal_exit.set()
            await loop_task

    asyncio.run(simulate_request_response_loop())

    assert not monitor_mission_request.success.has_event()
    assert not monitor_mission_request.failure.has_event()
