from typing import TYPE_CHECKING, List, Optional, Union

import isar.state_machine.states.going_to_lockdown as GoingToLockdown
import isar.state_machine.states.going_to_recharging as GoingToRecharging
import isar.state_machine.states.home as Home
import isar.state_machine.states.intervention_needed as InterventionNeeded
import isar.state_machine.states.pausing_return_home as PausingReturnHome
import isar.state_machine.states.stopping_due_to_maintenance as StoppingDueToMaintenance
import isar.state_machine.states.stopping_return_home as StoppingReturnHome
from isar.apis.models.models import (
    ControlMissionResponse,
    LockdownResponse,
    MissionStartResponse,
)
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import mission_started_event_handler
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import ReturnToHome

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturningHome(State):

    def __init__(self, state_machine: "StateMachine"):
        self.failed_return_home_attempts: int = 0
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _pause_mission_event_handler(
            should_pause: bool,
        ) -> Transition[PausingReturnHome.PausingReturnHome]:
            state_machine.events.api_requests.pause_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )
            state_machine.events.state_machine_events.pause_mission.trigger_event(True)
            return PausingReturnHome.transition()

        def _start_mission_event_handler(
            mission: Mission,
        ) -> Optional[Transition[StoppingReturnHome.StoppingReturnHome]]:
            # The check below is arguably not needed due to the battery eventhandler
            if not state_machine.battery_level_is_above_mission_start_threshold():
                response = MissionStartResponse(
                    mission_id=None,
                    mission_started=False,
                    mission_not_started_reason="Robot battery too low",
                )
                state_machine.events.api_requests.start_mission.response.trigger_event(
                    response
                )
                return None

            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingReturnHome.transition(mission)

        def _mission_status_event_handler(
            mission_status: MissionStatus,
        ) -> Optional[
            Union[
                Transition[InterventionNeeded.InterventionNeeded], Transition[Home.Home]
            ]
        ]:
            if mission_status and mission_status not in [
                MissionStatus.InProgress,
                MissionStatus.NotStarted,
                MissionStatus.Paused,
            ]:
                if mission_status != MissionStatus.Successful:
                    self.failed_return_home_attempts += 1
                    if (
                        self.failed_return_home_attempts
                        >= settings.RETURN_HOME_RETRY_LIMIT
                    ):
                        state_machine.logger.warning(
                            f"Failed to return home after {self.failed_return_home_attempts} attempts."
                        )
                        state_machine.publish_intervention_needed(
                            error_message=f"Return home failed after {self.failed_return_home_attempts} attempts."
                        )
                        return InterventionNeeded.transition()
                    else:
                        state_machine.start_mission(
                            Mission(
                                tasks=[ReturnToHome()],
                                name="Return Home",
                            )
                        )
                        return None

                return Home.transition()
            return None

        def _send_to_lockdown_event_handler(
            should_lockdown: bool,
        ) -> Transition[GoingToLockdown.GoingToLockdown]:
            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return GoingToLockdown.transition()

        def _mission_failed_event_handler(
            mission_failed: ErrorMessage,
        ) -> Transition[InterventionNeeded.InterventionNeeded]:
            state_machine.logger.warning(
                f"Failed to initiate return home because: "
                f"{mission_failed.error_description}"
            )
            state_machine.publish_intervention_needed(
                error_message="Return home failed to initiate."
            )
            return InterventionNeeded.transition()

        def _set_maintenance_mode_event_handler(
            should_set_maintenande_mode: bool,
        ) -> Transition[StoppingDueToMaintenance.StoppingDueToMaintenance]:
            state_machine.logger.warning(
                "Cancelling current mission due to robot going to maintenance mode"
            )
            state_machine.events.state_machine_events.stop_mission.trigger_event(True)
            return StoppingDueToMaintenance.transition("")

        def _robot_already_home_event_handler(
            already_home: bool,
        ) -> Transition[Home.Home]:
            state_machine.logger.info(
                "Robot reported that it is already home. "
                "Assuming return home mission successful without running."
            )
            return Home.transition()

        def _robot_battery_level_updated_handler(
            battery_level: float,
        ) -> Optional[Transition[GoingToRecharging.GoingToRecharging]]:
            if (
                battery_level is None
                or battery_level >= settings.ROBOT_MISSION_BATTERY_START_THRESHOLD
            ):
                return None

            return GoingToRecharging.transition()

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping(
                name="pause_mission_event",
                event=events.api_requests.pause_mission.request,
                handler=_pause_mission_event_handler,
            ),
            EventHandlerMapping(
                name="mission_started_event",
                event=events.robot_service_events.mission_started,
                handler=lambda event: mission_started_event_handler(
                    state_machine, event
                ),
            ),
            EventHandlerMapping(
                name="mission_failed_event",
                event=events.robot_service_events.mission_failed,
                handler=_mission_failed_event_handler,
            ),
            EventHandlerMapping(
                name="start_mission_event",
                event=events.api_requests.start_mission.request,
                handler=_start_mission_event_handler,
            ),
            EventHandlerMapping(
                name="mission_status_event",
                event=events.robot_service_events.mission_status_updated,
                handler=_mission_status_event_handler,
            ),
            EventHandlerMapping(
                name="robot_battery_update_event",
                event=shared_state.robot_battery_level,
                handler=_robot_battery_level_updated_handler,
                should_not_consume=True,
            ),
            EventHandlerMapping(
                name="send_to_lockdown_event",
                event=events.api_requests.send_to_lockdown.request,
                handler=_send_to_lockdown_event_handler,
            ),
            EventHandlerMapping(
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=_set_maintenance_mode_event_handler,
            ),
            EventHandlerMapping(
                name="robot_already_home",
                event=events.robot_service_events.robot_already_home,
                handler=_robot_already_home_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.ReturningHome,
            state_machine=state_machine,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[ReturningHome]:
    def _transition(state_machine: "StateMachine"):
        return ReturningHome(state_machine)

    return _transition
