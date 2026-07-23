import logging
from collections import deque
from typing import Deque

from isar.config.settings import settings
from isar.models.events import EmptyMessage, Events, SharedState
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
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    def __init__(
        self,
        events: Events,
        shared_state: SharedState,
        robot: RobotInterface,
        mqtt_publisher: MqttClientInterface,
    ):
        """Initializes the state machine.

        Parameters
        ----------
        events : Events
            Events used for API and robot service communication.
        robot : RobotInterface
            Instance of robot interface.
        mqtt_publisher : MqttClientInterface
            Instance of MQTT client interface which has a publish function

        """
        self.logger = logging.getLogger("state_machine")

        self.events: Events = events
        self.shared_state: SharedState = shared_state
        self.robot: RobotInterface = robot
        self.mqtt_publisher: MqttClientInterface | None = mqtt_publisher

        self.current_state: State = UnknownStatus(self.events)

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
                self.current_state = Maintenance(self.events)
            elif robot_startup_mode == RobotStartupMode.Lockdown:
                self.current_state = GoingToLockdown(self.events)

        self.transitions_list: Deque[States] = deque(
            [], settings.STATE_TRANSITIONS_LOG_LENGTH
        )

    #################################################################################

    def run(self) -> None:
        """Runs the state machine loop."""
        try:
            while True:
                self.update_state()
                transition: Transition | None = self.current_state.run()

                if transition is None:  # Expected when the thread is killed
                    self.logger.warning(
                        "Exiting state machine as next transition is None"
                    )
                    break

                next_state: State | None = transition(self.events)
                self.current_state = next_state
        except Exception as e:
            self.logger.error(f"Unhandled exception in state machine: {str(e)}")

    def terminate(self) -> None:
        self.logger.info("Stopping state machine")
        self.events.signal_state_machine_exit.trigger_event(EmptyMessage())

    def update_state(self) -> None:
        """Updates the current state of the state machine."""
        self.shared_state.state.update(self.current_state.name)

        if settings.USE_DB:
            if self.current_state.name in [
                States.StoppingGoToLockdown,
                States.GoingToLockdown,
                States.Lockdown,
            ]:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Lockdown,
                )
            elif self.current_state.name == States.Maintenance:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Maintenance,
                )
            else:
                change_persistent_robot_state(
                    settings.ISAR_ID,
                    value=RobotStartupMode.Normal,
                )

        self.transitions_list.append(self.current_state.name)
        self.logger.info("State: %s", self.current_state.name)
        publish_isar_status(self.mqtt_publisher, self._current_status())

    def _current_status(self) -> IsarStatus:
        if self.current_state.name == States.AwaitNextMission:
            return IsarStatus.Available
        elif self.current_state.name == States.ReturnHomePaused:
            return IsarStatus.ReturnHomePaused
        elif self.current_state.name == States.Paused:
            return IsarStatus.Paused
        elif self.current_state.name == States.Home:
            return IsarStatus.Home
        elif self.current_state.name == States.ReturningHome:
            return IsarStatus.ReturningHome
        elif self.current_state.name == States.Offline:
            return IsarStatus.Offline
        elif self.current_state.name == States.InterventionNeeded:
            return IsarStatus.InterventionNeeded
        elif self.current_state.name == States.Recharging:
            return IsarStatus.Recharging
        elif self.current_state.name == States.RechargingWithMission:
            return IsarStatus.RechargingWithMission
        elif self.current_state.name == States.Lockdown:
            return IsarStatus.Lockdown
        elif self.current_state.name == States.GoingToLockdown:
            return IsarStatus.GoingToLockdown
        elif self.current_state.name == States.GoingToRecharging:
            return IsarStatus.GoingToRecharging
        elif self.current_state.name == States.GoingToRechargingWithMission:
            return IsarStatus.GoingToRechargingWithMission
        elif self.current_state.name == States.Maintenance:
            return IsarStatus.Maintenance
        elif self.current_state.name == States.Pausing:
            return IsarStatus.Pausing
        elif self.current_state.name == States.PausingReturnHome:
            return IsarStatus.PausingReturnHome
        elif self.current_state.name in [
            States.Stopping,
            States.StoppingDueToMaintenance,
            States.StoppingGoToLockdown,
            States.StoppingGoToRecharge,
            States.StoppingPausedMission,
            States.StoppingPausedReturnHome,
        ]:
            return IsarStatus.Stopping
        elif self.current_state.name == States.StoppingReturnHome:
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
