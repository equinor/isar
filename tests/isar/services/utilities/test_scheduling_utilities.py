from http import HTTPStatus
from threading import Thread

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.models.events import APIEvent, Event, EventTimeoutError
from isar.services.utilities.scheduling_utilities import SchedulingUtilities
from isar.state_machine.state import State
from isar.state_machine.states_enum import States
from tests.test_mocks.mission_definition import DummyMissionDefinition


def test_timeout_send_command(
    mocker: MockerFixture, scheduling_utilities: SchedulingUtilities
) -> None:
    mocker.patch.object(settings, "QUEUE_TIMEOUT", 2)
    mocker.patch.object(Event, "consume_event", side_effect=EventTimeoutError)
    mocker.patch.object(
        SchedulingUtilities, "_verify_valid_state", lambda self, event: None
    )
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
    mocker: MockerFixture,
    all_states_dict: dict[States, State],
) -> None:
    events = scheduling_utilities.state_machine.events
    api_events = events.api_requests

    all_states = list(all_states_dict.keys())

    event_mappings: dict[APIEvent, list[States]] = {
        api_events.start_mission: [
            States.Home,
            States.AwaitNextMission,
            States.ReturningHome,
            States.ReturnHomePaused,
        ],
        api_events.stop_mission: [
            States.Monitor,
            States.GoingToRechargingWithMission,
            States.RechargingWithMission,
            States.AwaitNextMission,
            States.Paused,
            States.Home,
            States.UnknownStatus,
        ],
        api_events.pause_mission: [States.Monitor, States.ReturningHome],
        api_events.resume_mission: [States.Paused, States.ReturnHomePaused],
        api_events.send_to_lockdown: all_states,
        api_events.release_from_lockdown: [States.Lockdown, States.LockdownWithMission],
        api_events.set_maintenance_mode: all_states,
        api_events.release_from_maintenance_mode: [States.Maintenance],
        api_events.release_intervention_needed: [States.InterventionNeeded],
        api_events.return_home: [
            States.AwaitNextMission,
            States.Home,
            States.InterventionNeeded,
        ],
    }

    for event, valid_states in event_mappings.items():
        mocker.patch.object(event.request, "trigger_event", lambda input, timeout: None)
        mocker.patch.object(event.response, "consume_event", lambda timeout: None)
        for state_name, state_object in all_states_dict.items():
            scheduling_utilities.state_machine.current_state = state_object
            if state_name in valid_states:
                try:
                    scheduling_utilities._send_command(True, event)
                except HTTPException:
                    assert (
                        False
                    ), f"Failed to send event {event.request.name} in state {state_name}"
            else:
                try:
                    scheduling_utilities._send_command(True, event)
                    pytest.fail(
                        f"Event {event.request.name} succeeded in state {state_name}"
                    )
                except Exception as e:  # noqa: BLE001
                    assert (
                        e.__class__ == HTTPException
                    ), f"Event {event.request.name} failed in state {state_name} with an incorrect exception type {e.__class__}"
    assert True


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
    mocker: MockerFixture, scheduling_utilities: SchedulingUtilities
) -> None:
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
