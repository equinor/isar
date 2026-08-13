import isar.state_machine.states.lockdown as Lockdown
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.monitor as Monitor
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.recharging as Recharging
from isar.apis.models.models import ControlMissionResponse
from isar.models.events import AbortedMission, EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


class RechargingWithMission(State):

    def __init__(self, events: Events, mission: AbortedMission):

        def _stop_mission_event_handler(
            stop_mission_id: str,
        ) -> Transition[Recharging.Recharging] | None:
            if mission.id == stop_mission_id or stop_mission_id == "":
                events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(success=True)
                )
                return Recharging.transition()
            else:
                events.api_requests.stop_mission.response.trigger_event(
                    ControlMissionResponse(
                        success=False, failure_reason="Mission not found"
                    )
                )
                return None

        event_handlers: list[EventHandlerMapping] = [
            EventHandlerMapping[EmptyMessage](
                event=events.robot_service_events.battery_above_recharge_threshold_event,
                handler=lambda _: Monitor.transition_and_start_mission(
                    mission, should_respond_to_API_request=False
                ),
            ),
            EventHandlerMapping[RobotStatus](
                event=events.robot_service_events.robot_status_update,
                handler=lambda robot_status: (
                    Offline.transition()
                    if robot_status == RobotStatus.Offline
                    else None
                ),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.send_to_lockdown.request,
                handler=lambda _: Lockdown.transition_and_respond_to_api(),
            ),
            EventHandlerMapping[EmptyMessage](
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
            EventHandlerMapping[str](
                event=events.api_requests.stop_mission.request,
                handler=_stop_mission_event_handler,
            ),
        ]
        super().__init__(
            state_name=States.RechargingWithMission,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition(mission: AbortedMission) -> Transition[RechargingWithMission]:
    def _transition(events: Events) -> RechargingWithMission:
        return RechargingWithMission(events, mission=mission)

    return _transition
