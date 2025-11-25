import json
import logging
from collections import deque
from datetime import datetime, timezone
from threading import Event
from typing import Deque, List, Optional

from transitions import Machine
from transitions.core import State

from isar.config.settings import settings
from isar.models.events import Events, SharedState
from isar.models.status import IsarStatus
from isar.services.service_connections.persistent_memory import (
    NoSuchRobotException,
    create_persistent_robot_state,
    read_persistent_robot_state_is_maintenance_mode,
)
from isar.services.utilities.mqtt_utilities import publish_isar_status
from isar.state_machine.states.await_next_mission import AwaitNextMission
from isar.state_machine.states.blocked_protective_stop import BlockedProtectiveStop
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.lockdown import Lockdown
from isar.state_machine.states.maintenance import Maintenance
from isar.state_machine.states.monitor import Monitor
from isar.state_machine.states.offline import Offline
from isar.state_machine.states.paused import Paused
from isar.state_machine.states.pausing import Pausing
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.recharging import Recharging
from isar.state_machine.states.resuming import Resuming
from isar.state_machine.states.resuming_return_home import ResumingReturnHome
from isar.state_machine.states.return_home_paused import ReturnHomePaused
from isar.state_machine.states.returning_home import ReturningHome
from isar.state_machine.states.stopping import Stopping
from isar.state_machine.states.stopping_due_to_maintenance import (
    StoppingDueToMaintenance,
)
from isar.state_machine.states.stopping_go_to_lockdown import StoppingGoToLockdown
from isar.state_machine.states.stopping_go_to_recharge import StoppingGoToRecharge
from isar.state_machine.states.stopping_paused_mission import StoppingPausedMission
from isar.state_machine.states.stopping_paused_return_home import (
    StoppingPausedReturnHome,
)
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from isar.state_machine.states.unknown_status import UnknownStatus
from isar.state_machine.states_enum import States
from isar.state_machine.transitions.mission import get_mission_transitions
from isar.state_machine.transitions.return_home import get_return_home_transitions
from isar.state_machine.transitions.robot_status import get_robot_status_transitions
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

        # List of states
        # States running mission
        self.monitor_state: State = Monitor(self)
        self.returning_home_state: State = ReturningHome(self)
        self.stopping_state: State = Stopping(self)
        self.paused_state: State = Paused(self)
        self.pausing_state: State = Pausing(self)
        self.return_home_paused_state: State = ReturnHomePaused(self)
        self.stopping_return_home_state: State = StoppingReturnHome(self)
        self.pausing_return_home_state: State = PausingReturnHome(self)
        self.resuming_state: State = Resuming(self)
        self.resuming_return_home_state: State = ResumingReturnHome(self)
        self.stopping_go_to_lockdown_state: State = StoppingGoToLockdown(self)
        self.stopping_go_to_recharge_state: State = StoppingGoToRecharge(self)
        self.going_to_lockdown_state: State = GoingToLockdown(self)
        self.going_to_recharging_state: State = GoingToRecharging(self)
        self.stopping_due_to_maintenance_state: State = StoppingDueToMaintenance(self)
        self.stopping_paused_mission_state: State = StoppingPausedMission(self)
        self.stopping_paused_return_home_state: State = StoppingPausedReturnHome(self)

        # States Waiting for mission
        self.await_next_mission_state: State = AwaitNextMission(self)
        self.home_state: State = Home(self)
        self.intervention_needed_state: State = InterventionNeeded(self)

        # Status states
        self.offline_state: State = Offline(self)
        self.blocked_protective_stopping_state: State = BlockedProtectiveStop(self)
        self.recharging_state: State = Recharging(self)
        self.lockdown_state: State = Lockdown(self)
        self.maintenance_state: State = Maintenance(self)

        # Error and special status states
        self.unknown_status_state: State = UnknownStatus(self)

        self.states: List[State] = [
            self.monitor_state,
            self.returning_home_state,
            self.stopping_state,
            self.stopping_return_home_state,
            self.pausing_return_home_state,
            self.paused_state,
            self.pausing_state,
            self.resuming_state,
            self.return_home_paused_state,
            self.await_next_mission_state,
            self.home_state,
            self.offline_state,
            self.blocked_protective_stopping_state,
            self.unknown_status_state,
            self.intervention_needed_state,
            self.recharging_state,
            self.stopping_go_to_lockdown_state,
            self.resuming_return_home_state,
            self.going_to_lockdown_state,
            self.lockdown_state,
            self.going_to_recharging_state,
            self.stopping_go_to_recharge_state,
            self.stopping_due_to_maintenance_state,
            self.maintenance_state,
            self.stopping_paused_mission_state,
            self.stopping_paused_return_home_state,
        ]

        if settings.PERSISTENT_STORAGE_CONNECTION_STRING == "":
            initial_state = "unknown_status"
            self.logger.warning(
                "PERSISTENT_STORAGE_CONNECTION_STRING is not set. Restarting ISAR will forget the state, including maintenance mode. "
            )
        else:
            is_maintenance_mode = read_or_create_persistent_maintenance_mode()
            self.logger.info(
                f"Connected to robot status database and the maintenance mode was: {is_maintenance_mode}. "
            )
            if is_maintenance_mode:
                initial_state = "maintenance"
            else:
                initial_state = "unknown_status"

        self.machine = Machine(
            self, states=self.states, initial=initial_state, queued=True
        )

        self.transitions: List[dict] = []

        self.transitions.extend(get_mission_transitions(self))
        self.transitions.extend(get_return_home_transitions(self))
        self.transitions.extend(get_robot_status_transitions(self))

        self.machine.add_transitions(self.transitions)

        self.current_state: State = States(self.state)  # type: ignore

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
        self.transitions = []

    def begin(self):
        """Starts the state machine. Transitions into unknown status state."""
        self.initial_transition()  # type: ignore

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
        self.current_state = States(self.state)  # type: ignore
        self.shared_state.state.update(self.current_state)
        self.transitions_list.append(self.current_state)
        self.logger.info("State: %s", self.current_state)
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

    def publish_mission_aborted(self, reason: str, can_be_continued: bool) -> None:
        if not self.mqtt_publisher:
            return

        if self.shared_state.mission_id.check() is None:
            self.logger.warning(
                "Publishing mission aborted message with no ongoing mission."
            )

        payload: MissionAbortedPayload = MissionAbortedPayload(
            isar_id=settings.ISAR_ID,
            robot_name=settings.ROBOT_NAME,
            mission_id=self.shared_state.mission_id.check(),
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
        if self.current_state == States.AwaitNextMission:
            return IsarStatus.Available
        elif self.current_state == States.ReturnHomePaused:
            return IsarStatus.ReturnHomePaused
        elif self.current_state == States.Paused:
            return IsarStatus.Paused
        elif self.current_state == States.Home:
            return IsarStatus.Home
        elif self.current_state == States.ReturningHome:
            return IsarStatus.ReturningHome
        elif self.current_state == States.Offline:
            return IsarStatus.Offline
        elif self.current_state == States.BlockedProtectiveStop:
            return IsarStatus.BlockedProtectiveStop
        elif self.current_state == States.InterventionNeeded:
            return IsarStatus.InterventionNeeded
        elif self.current_state == States.Recharging:
            return IsarStatus.Recharging
        elif self.current_state == States.Lockdown:
            return IsarStatus.Lockdown
        elif self.current_state == States.GoingToLockdown:
            return IsarStatus.GoingToLockdown
        elif self.current_state == States.GoingToRecharging:
            return IsarStatus.GoingToRecharging
        elif self.current_state == States.Maintenance:
            return IsarStatus.Maintenance
        elif self.current_state == States.Pausing:
            return IsarStatus.Pausing
        elif self.current_state == States.PausingReturnHome:
            return IsarStatus.PausingReturnHome
        elif self.current_state in [
            States.Stopping,
            States.StoppingDueToMaintenance,
            States.StoppingGoToLockdown,
            States.StoppingGoToRecharge,
            States.StoppingPausedMission,
            States.StoppingPausedReturnHome,
        ]:
            return IsarStatus.Stopping
        elif self.current_state == States.StoppingReturnHome:
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
    state_machine.begin()
