import json
import logging
from collections import deque
from datetime import datetime, timezone
from threading import Event
from typing import Deque, Optional

from isar.config.settings import settings
from isar.eventhandlers.eventhandler import State
from isar.models.events import Events, SharedState
from isar.models.status import IsarStatus
from isar.services.service_connections.persistent_memory import (
    NoSuchRobotException,
    create_persistent_robot_state,
    read_persistent_robot_state_is_maintenance_mode,
)
from isar.services.utilities.mqtt_utilities import publish_isar_status
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import ReturnToHome
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.telemetry.payloads import (
    InterventionNeededPayload,
    MissionAbortedPayload,
)
from robot_interface.utilities.json_service import EnhancedJSONEncoder


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
        self.mqtt_publisher: Optional[MqttClientInterface] = mqtt_publisher

        self.signal_state_machine_to_stop: Event = Event()

        self.current_state: State = UnknownStatus(self)

        if settings.PERSISTENT_STORAGE_CONNECTION_STRING == "":
            self.logger.warning(
                "PERSISTENT_STORAGE_CONNECTION_STRING is not set. Restarting ISAR will forget the state, including maintenance mode. "
            )
        else:
            is_maintenance_mode = read_or_create_persistent_maintenance_mode()
            self.logger.info(
                f"Connected to robot status database and the maintenance mode was: {is_maintenance_mode}. "
            )
            if is_maintenance_mode:
                self.current_state = Maintenance(self)

        self.transitions_list: Deque[States] = deque(
            [], settings.STATE_TRANSITIONS_LOG_LENGTH
        )

    #################################################################################

    def print_transitions(self) -> None:
        state_transitions: str = ", ".join(
            [
                f"\n  {transition}" if (i + 1) % 10 == 0 else f"{transition}"
                for i, transition in enumerate(list(self.transitions_list))
            ]
        )
        self.logger.info("State transitions:\n  %s", state_transitions)
        self.transitions_list.clear()

    def run(self):
        """Runs the state machine loop."""
        try:
            while self.current_state is not None:
                self.update_state()
                self.current_state = self.current_state.run()
                if self.current_state is None:
                    self.logger.warning(
                        "Exiting state machine as current state is None"
                    )
        except Exception as e:
            self.logger.error(f"Unhandled exception in state machine: {str(e)}")

    def terminate(self):
        self.logger.info("Stopping state machine")
        self.signal_state_machine_to_stop.set()

    def battery_level_is_above_mission_start_threshold(self):
        if not self.shared_state.robot_battery_level.check():
            self.logger.warning("Battery level is None")
            return False
        return (
            not self.shared_state.robot_battery_level.check()
            < settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
        )

    def update_state(self):
        """Updates the current state of the state machine."""
        self.shared_state.state.update(self.current_state.name)
        self.transitions_list.append(self.current_state.name)
        self.logger.info("State: %s", self.current_state.name)
        self.publish_status()

    def start_mission(self, mission: Mission):
        """Starts a scheduled mission."""
        self.events.state_machine_events.start_mission.trigger_event(mission)

    def start_return_home_mission(self):
        """Starts a return to home mission."""
        mission = Mission(
            tasks=[ReturnToHome()],
            name="Return Home",
        )
        self.events.state_machine_events.start_mission.trigger_event(mission)

    def publish_mission_aborted(
        self, current_mission_id: Optional[str], reason: str, can_be_continued: bool
    ) -> None:
        if not self.mqtt_publisher:
            return

        if current_mission_id is None:
            self.logger.warning(
                "Publishing mission aborted message with no ongoing mission."
            )

        payload: MissionAbortedPayload = MissionAbortedPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=current_mission_id,
            reason=reason,
            can_be_continued=can_be_continued,
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_MISSION_ABORTED,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def publish_intervention_needed(self, error_message: str) -> None:
        """Publishes the intervention needed message to the MQTT Broker"""
        if not self.mqtt_publisher:
            return

        payload: InterventionNeededPayload = InterventionNeededPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            reason=error_message,
            timestamp=datetime.now(timezone.utc),
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_INTERVENTION_NEEDED,
            payload=json.dumps(payload, cls=EnhancedJSONEncoder),
            qos=1,
            retain=True,
        )

    def publish_status(self) -> None:
        if not self.mqtt_publisher:
            return

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
        elif self.current_state.name == States.BlockedProtectiveStop:
            return IsarStatus.BlockedProtectiveStop
        elif self.current_state.name == States.InterventionNeeded:
            return IsarStatus.InterventionNeeded
        elif self.current_state.name == States.Recharging:
            return IsarStatus.Recharging
        elif self.current_state.name == States.Lockdown:
            return IsarStatus.Lockdown
        elif self.current_state.name == States.GoingToLockdown:
            return IsarStatus.GoingToLockdown
        elif self.current_state.name == States.GoingToRecharging:
            return IsarStatus.GoingToRecharging
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


def read_or_create_persistent_maintenance_mode():
    try:
        is_maintenance_mode = read_persistent_robot_state_is_maintenance_mode(
            settings.PERSISTENT_STORAGE_CONNECTION_STRING, settings.ISAR_ID
        )
    except NoSuchRobotException:
        create_persistent_robot_state(
            settings.PERSISTENT_STORAGE_CONNECTION_STRING, settings.ISAR_ID
        )
        is_maintenance_mode = read_persistent_robot_state_is_maintenance_mode(
            settings.PERSISTENT_STORAGE_CONNECTION_STRING, settings.ISAR_ID
        )
    return is_maintenance_mode


def main(state_machine: StateMachine):
    """Starts a state machine instance."""
    state_machine.run()
