from typing import Optional, cast

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerBase, EventHandlerMapping
from isar.state_machine.state_machine import StateMachine
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage, ErrorReason
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import TakeImage, Task
from tests.test_mocks.pose import DummyPose


def test_transition_from_return_home_paused_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.state = sync_state_machine.return_home_paused_state.name  # type: ignore

    return_home_paused_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.return_home_paused_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        return_home_paused_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    going_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_lockdown_state
    )
    lockdown_event_handler: Optional[EventHandlerMapping] = (
        going_to_lockdown_state.get_event_handler_by_name("mission_failed_to_resume")
    )
    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.resume_lockdown  # type: ignore
    transition()

    assert sync_state_machine.events.api_requests.send_to_lockdown.response.has_event()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore

    lockdown_event_handler.event.trigger_event(
        ErrorMessage(
            error_description="Test going to lockdown resume return to home mission failed",
            error_reason=ErrorReason.RobotCommunicationException,
        )
    )
    transition = lockdown_event_handler.handler(lockdown_event_handler.event)

    assert transition is sync_state_machine.lockdown_mission_failed  # type: ignore

    transition()
    assert sync_state_machine.state is sync_state_machine.intervention_needed_state.name  # type: ignore


def test_stopping_lockdown_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    task_1: Task = TakeImage(
        target=DummyPose.default_pose().position, robot_pose=DummyPose.default_pose()
    )
    sync_state_machine.shared_state.mission_id.trigger_event(
        Mission(name="Dummy misson", tasks=[task_1])
    )
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.stopping_go_to_lockdown_state.name  # type: ignore

    stopping_go_to_lockdown_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.stopping_go_to_lockdown_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        stopping_go_to_lockdown_state.get_event_handler_by_name("successful_stop_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.start_lockdown_mission_monitoring  # type: ignore
    assert (
        sync_state_machine.events.api_requests.send_to_lockdown.response.check().lockdown_started
    )

    assert not sync_state_machine.events.mqtt_queue.empty()
    mqtt_message = sync_state_machine.events.mqtt_queue.get(block=False)
    assert mqtt_message is not None
    mqtt_payload_topic = mqtt_message[0]
    assert mqtt_payload_topic is settings.TOPIC_ISAR_MISSION_ABORTED

    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore


def test_return_home_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.returning_home_state.name  # type: ignore

    returning_home_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.returning_home_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        returning_home_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.go_to_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore


def test_recharging_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.going_to_recharging_state.name  # type: ignore

    going_to_recharging_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.going_to_recharging_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        going_to_recharging_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.go_to_lockdown  # type: ignore
    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore


def test_await_next_mission_transitions_to_going_to_lockdown(
    sync_state_machine: StateMachine,
) -> None:
    sync_state_machine.shared_state.robot_battery_level.trigger_event(10.0)
    sync_state_machine.state = sync_state_machine.await_next_mission_state.name  # type: ignore

    await_next_mission_state: EventHandlerBase = cast(
        EventHandlerBase, sync_state_machine.await_next_mission_state
    )
    event_handler: Optional[EventHandlerMapping] = (
        await_next_mission_state.get_event_handler_by_name("send_to_lockdown_event")
    )

    assert event_handler is not None

    event_handler.event.trigger_event(True)
    transition = event_handler.handler(event_handler.event)

    assert transition is sync_state_machine.start_lockdown_mission_monitoring  # type: ignore
    assert sync_state_machine.events.api_requests.send_to_lockdown.response.check()
    transition()
    assert sync_state_machine.state is sync_state_machine.going_to_lockdown_state.name  # type: ignore
