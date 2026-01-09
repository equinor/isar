from http import HTTPStatus
from threading import Thread

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.models.events import APIEvent, Event, EventTimeoutError
from isar.modules import ApplicationContainer
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state_machine import StateMachine
from isar.state_machine.states_enum import States
from tests.test_mocks.mission_definition import DummyMissionDefinition


def test_timeout_send_command(
    mocker: MockerFixture, scheduling_utilities: SchedulingUtilities
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    mocker.patch.object(Event, "consume_event", side_effect=EventTimeoutError)
    q: APIEvent = APIEvent("test")
    with pytest.raises(EventTimeoutError):
        scheduling_utilities._send_command(True, q)
    assert q.request.empty()


def test_robot_capable_of_mission(scheduling_utilities: SchedulingUtilities) -> None:
    assert scheduling_utilities.verify_robot_capable_of_mission(
        mission=DummyMissionDefinition.default_mission,
        robot_capabilities=["return_to_home", "take_image"],
    )


def test_robot_not_capable_of_mission(
    scheduling_utilities: SchedulingUtilities,
) -> None:
    with pytest.raises(HTTPException) as err:
        scheduling_utilities.verify_robot_capable_of_mission(
            mission=DummyMissionDefinition.default_mission,
            robot_capabilities=["return_to_home"],
        )
    assert err.value.status_code == HTTPStatus.BAD_REQUEST


def test_state_machine_ready_to_receive_mission(
    scheduling_utilities: SchedulingUtilities,
) -> None:
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.Home
    )
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.ReturningHome
    )
    assert scheduling_utilities.verify_state_machine_ready_to_receive_mission(
        States.AwaitNextMission
    )


def test_state_machine_not_ready_to_receive_mission(
    scheduling_utilities: SchedulingUtilities,
) -> None:
    with pytest.raises(HTTPException) as err:
        scheduling_utilities.verify_state_machine_ready_to_receive_mission(
            States.Monitor
        )
    assert err.value.status_code == HTTPStatus.CONFLICT


def test_mission_already_started_causes_conflict(
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    start_mission_thread: Thread = Thread(
        target=scheduling_utilities.start_mission,
        args=[DummyMissionDefinition.default_mission],
    )
    start_mission_thread.start()

    with pytest.raises(HTTPException) as err:
        scheduling_utilities.start_mission(DummyMissionDefinition.default_mission)
    start_mission_thread.join()
    assert err.value.status_code == HTTPStatus.CONFLICT


def test_pause_mission_twice_causes_conflict(
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    pause_mission_thread: Thread = Thread(target=scheduling_utilities.pause_mission)
    pause_mission_thread.start()

    with pytest.raises(HTTPException) as err:
        scheduling_utilities.pause_mission()
    pause_mission_thread.join()
    assert err.value.status_code == HTTPStatus.CONFLICT


def test_resume_mission_twice_causes_conflict(
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    resume_mission_thread: Thread = Thread(target=scheduling_utilities.resume_mission)
    resume_mission_thread.start()

    with pytest.raises(HTTPException) as err:
        scheduling_utilities.resume_mission()
    resume_mission_thread.join()
    assert err.value.status_code == HTTPStatus.CONFLICT


def test_stop_mission_twice_causes_conflict(
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    stop_mission_thread: Thread = Thread(target=scheduling_utilities.stop_mission)
    stop_mission_thread.start()

    with pytest.raises(HTTPException) as err:
        scheduling_utilities.stop_mission()
    stop_mission_thread.join()
    assert err.value.status_code == HTTPStatus.CONFLICT


def test_return_home_twice_causes_conflict(
    scheduling_utilities: SchedulingUtilities,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    return_home_thread: Thread = Thread(target=scheduling_utilities.return_home)
    return_home_thread.start()

    with pytest.raises(HTTPException) as err:
        scheduling_utilities.return_home()
    return_home_thread.join()
    assert err.value.status_code == HTTPStatus.CONFLICT


def test_api_with_unsuccessful_return_home_stop(
    mocker: MockerFixture,
    container: ApplicationContainer,
    sync_state_machine: StateMachine,
) -> None:
    scheduling_utilities: SchedulingUtilities = container.scheduling_utilities()
    stopped_mission_response: ControlMissionResponse = ControlMissionResponse(
        success=False, failure_reason="ISAR failed to stop mission"
    )
    mocker.patch.object(
        Event,
        "consume_event",
        return_value=stopped_mission_response,
    )

    with pytest.raises(HTTPException) as exception_details:
        scheduling_utilities.stop_mission()

    assert exception_details.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE.value
