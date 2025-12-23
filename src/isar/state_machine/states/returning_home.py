from typing import TYPE_CHECKING, List, Optional, Union

from isar.apis.models.models import (
    ControlMissionResponse,
    LockdownResponse,
    MissionStartResponse,
)
from isar.config.settings import settings
from isar.eventhandlers.eventhandler import EventHandlerMapping, State, Transition
from isar.models.events import Event
from isar.state_machine.states.going_to_lockdown import GoingToLockdown
from isar.state_machine.states.going_to_recharging import GoingToRecharging
from isar.state_machine.states.home import Home
from isar.state_machine.states.intervention_needed import InterventionNeeded
from isar.state_machine.states.pausing_return_home import PausingReturnHome
from isar.state_machine.states.stopping_due_to_maintenance import (
    StoppingDueToMaintenance,
)
from isar.state_machine.states.stopping_return_home import StoppingReturnHome
from isar.state_machine.states_enum import States
from isar.state_machine.utils.common_event_handlers import mission_started_event_handler
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus
from robot_interface.models.mission.task import ReturnToHome

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class ReturningHome(State):

    @staticmethod
    def transition() -> Transition["ReturningHome"]:
        def _transition(state_machine: "StateMachine"):
            return ReturningHome(state_machine)

        return _transition

    def __init__(self, state_machine: "StateMachine"):
        self.failed_return_home_attempts: int = 0
        events = state_machine.events
        shared_state = state_machine.shared_state

        def _pause_mission_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[PausingReturnHome]]:
            if not event.consume_event():
                return None

            state_machine.events.api_requests.pause_mission.response.trigger_event(
                ControlMissionResponse(success=True)
            )
            state_machine.events.state_machine_events.pause_mission.trigger_event(True)
            return PausingReturnHome.transition()

        def _start_mission_event_handler(
            event: Event[Mission],
        ) -> Optional[Transition[StoppingReturnHome]]:
            mission = event.consume_event()
            if not mission:
                return None

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
            event: Event[MissionStatus],
        ) -> Optional[Union[Transition[InterventionNeeded], Transition[Home]]]:
            mission_status: Optional[MissionStatus] = event.consume_event()

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
                        state_machine.print_transitions()
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
            event: Event[bool],
        ) -> Optional[Transition[GoingToLockdown]]:
            should_lockdown: bool = event.consume_event()
            if not should_lockdown:
                return None

            events.api_requests.send_to_lockdown.response.trigger_event(
                LockdownResponse(lockdown_started=True)
            )
            return GoingToLockdown.transition()

        def _mission_failed_event_handler(
            event: Event[Optional[ErrorMessage]],
        ) -> Optional[Transition[InterventionNeeded]]:
            mission_failed: Optional[ErrorMessage] = event.consume_event()
            if mission_failed is not None:
                state_machine.logger.warning(
                    f"Failed to initiate return home because: "
                    f"{mission_failed.error_description}"
                )
                state_machine.publish_intervention_needed(
                    error_message="Return home failed to initiate."
                )
                state_machine.print_transitions()
                return InterventionNeeded.transition()
            return None

        def _set_maintenance_mode_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[StoppingDueToMaintenance]]:
            should_set_maintenande_mode: bool = event.consume_event()
            if should_set_maintenande_mode:
                state_machine.logger.warning(
                    "Cancelling current mission due to robot going to maintenance mode"
                )
                state_machine.events.state_machine_events.stop_mission.trigger_event(
                    True
                )
                return StoppingDueToMaintenance.transition("")
            return None

        def _robot_already_home_event_handler(
            event: Event[bool],
        ) -> Optional[Transition[Home]]:
            already_home: bool = event.consume_event()
            if already_home:
                state_machine.logger.info(
                    "Robot reported that it is already home. "
                    "Assuming return home mission successful without running."
                )
                return Home.transition()
            return None

        def _robot_battery_level_updated_handler(
            event: Event[float],
        ) -> Optional[Transition[GoingToRecharging]]:
            battery_level: float = event.check()
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
