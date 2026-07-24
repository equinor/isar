import logging
from collections import deque
from typing import Deque

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Event, Events
from isar.models.status import IsarStatus
from isar.services.service_connections.persistent_memory import (
    NoSuchRobotException,
    RobotStartupMode,
    change_persistent_robot_state,
    create_persistent_robot_state,
    read_persistent_robot_state,
)
from isar.services.utilities.mqtt_utilities import publish_isar_status
from isar.state_machine.state import State, Transition
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from robot_interface.telemetry.mqtt_client import MqttClientInterface


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    def __init__(
        self,
        events: Events,
        mqtt_publisher: MqttClientInterface,
    ):
        """Initializes the state machine.

        Parameters
        ----------
        events : Events
            Events used for API and robot service communication.
        mqtt_publisher : MqttClientInterface
            Instance of MQTT client interface which has a publish function

        """
        self.logger = logging.getLogger("state_machine")

        self.events: Events = events
        self.state_event: Event[States] = events.state
        self.mqtt_publisher: MqttClientInterface | None = mqtt_publisher

        self.starting_state: State = UnknownStatus(self.events)

        if not settings.USE_DB:
            self.logger.warning(
                "Not using ISAR database. Restarting ISAR will forget the state, including maintenance mode. "
            )
        else:
            robot_startup_mode = read_or_create_persistent_mode()
            self.logger.info(
                f"Connected to robot status database and the startup mode was: {robot_startup_mode}. "
            )
            if robot_startup_mode == RobotStartupMode.Maintenance:
                self.starting_state = Maintenance(self.events)
            elif robot_startup_mode == RobotStartupMode.Lockdown:
                self.starting_state = GoingToLockdown(self.events)

        self.transitions_list: Deque[States] = deque(
            [], settings.STATE_TRANSITIONS_LOG_LENGTH
        )

        self.state_event.update(self.starting_state.name)

    #################################################################################

    def run(self) -> None:
        """Runs the state machine loop."""
        current_state = self.starting_state
        try:
            while True:
                self.update_state(current_state)
                transition: Transition | None = current_state.run()

                if transition is None:  # Expected when the thread is killed
                    self.logger.warning(
                        "Exiting state machine as next transition is None"
                    )
                    break

                next_state: State | None = transition(self.events)
                current_state = next_state
        except Exception as e:
            self.logger.error(f"Unhandled exception in state machine: {str(e)}")

    def terminate(self) -> None:
        self.logger.info("Stopping state machine")
        self.events.signal_state_machine_exit.trigger_event(EmptyMessage())

    def update_state(self, current_state: State) -> None:
        """Updates the current state of the state machine."""
        self.state_event.update(current_state.name)

        if settings.USE_DB:
            if current_state.name in [
                States.StoppingGoToLockdown,
                States.GoingToLockdown,
                States.Lockdown,
            ]:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Lockdown,
                )
            elif current_state.name == States.Maintenance:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Maintenance,
                )
            else:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Normal,
                )

        self.transitions_list.append(current_state.name)
        self.logger.info("State: %s", current_state.name)
        publish_isar_status(self.mqtt_publisher, state_to_status(current_state.name))


def state_to_status(state_name: States) -> IsarStatus:
    if state_name == States.AwaitNextMission:
        return IsarStatus.Available
    elif state_name == States.ReturnHomePaused:
        return IsarStatus.ReturnHomePaused
    elif state_name == States.Paused:
        return IsarStatus.Paused
    elif state_name == States.Home:
        return IsarStatus.Home
    elif state_name == States.ReturningHome:
        return IsarStatus.ReturningHome
    elif state_name == States.Offline:
        return IsarStatus.Offline
    elif state_name == States.InterventionNeeded:
        return IsarStatus.InterventionNeeded
    elif state_name == States.Recharging:
        return IsarStatus.Recharging
    elif state_name == States.RechargingWithMission:
        return IsarStatus.RechargingWithMission
    elif state_name == States.Lockdown:
        return IsarStatus.Lockdown
    elif state_name == States.GoingToLockdown:
        return IsarStatus.GoingToLockdown
    elif state_name == States.GoingToRecharging:
        return IsarStatus.GoingToRecharging
    elif state_name == States.GoingToRechargingWithMission:
        return IsarStatus.GoingToRechargingWithMission
    elif state_name == States.Maintenance:
        return IsarStatus.Maintenance
    elif state_name == States.Pausing:
        return IsarStatus.Pausing
    elif state_name == States.PausingReturnHome:
        return IsarStatus.PausingReturnHome
    elif state_name in [
        States.Stopping,
        States.StoppingDueToMaintenance,
        States.StoppingGoToLockdown,
        States.StoppingGoToRecharge,
        States.StoppingPausedMission,
        States.StoppingPausedReturnHome,
    ]:
        return IsarStatus.Stopping
    elif state_name == States.StoppingReturnHome:
        return IsarStatus.StoppingReturnHome
    else:
        return IsarStatus.Busy


def read_or_create_persistent_mode() -> RobotStartupMode:
    try:
        startup_mode = read_persistent_robot_state(settings.ISAR_ID)
    except NoSuchRobotException:
        create_persistent_robot_state(
            settings.ISAR_ID,
            RobotStartupMode.Maintenance,
        )
        startup_mode = read_persistent_robot_state(settings.ISAR_ID)
        logger = logging.getLogger("state_machine")
        logger.info(
            f"Created new persistent robot state for robot id {settings.ISAR_ID}. It is now set to: {startup_mode}."
        )
    return startup_mode
