from typing import List

import isar.state_machine.states.await_next_mission as AwaitNextMission
import isar.state_machine.states.home as Home
import isar.state_machine.states.maintenance as Maintenance
import isar.state_machine.states.offline as Offline
import isar.state_machine.states.stopping as Stopping
import isar.state_machine.states.stopping_unknown_mission as StoppingUnknownMission
from isar.models.events import EmptyMessage, Events
from isar.state_machine.state import EventHandlerMapping, State, Transition
from isar.state_machine.states_enum import States
from robot_interface.models.mission.status import RobotStatus


class UnknownStatus(State):

    def __init__(self, events: Events):

        def _robot_status_event_handler(
            robot_status: RobotStatus,
        ) -> (
            Transition[Home.Home]
            | Transition[AwaitNextMission.AwaitNextMission]
            | Transition[Offline.Offline]
            | Transition[Maintenance.Maintenance]
            | Transition[StoppingUnknownMission.StoppingUnknownMission]
            | None
        ):
            if robot_status == RobotStatus.Home:
                self.logger.info(
                    "Got robot status home while in unknown status state. Leaving unknown status state."
                )
                return Home.transition()
            elif robot_status == RobotStatus.Available:
                self.logger.info(
                    "Got robot status available while in unknown status state. Leaving unknown status state."
                )
                return AwaitNextMission.transition()
            elif robot_status == RobotStatus.Offline:
                self.logger.info(
                    "Got robot status offline while in unknown status state. Leaving unknown status state."
                )
                return Offline.transition()
            elif robot_status == RobotStatus.TeleOperation:
                self.logger.info(
                    "Got robot status teleoperation while in unknown status state. Leaving unknown status state."
                )
                return Maintenance.transition_without_replying_to_API()
            elif robot_status == RobotStatus.Busy:
                self.logger.info(
                    "Got robot status busy while in unknown status state. Leaving unknown status state."
                )
                return StoppingUnknownMission.transition()
            return None

        event_handlers: List[EventHandlerMapping] = [
            EventHandlerMapping[str](
                name="stop_mission_event",
                event=events.api_requests.stop_mission.request,
                handler=lambda mission_id: Stopping.transition_and_trigger_stop_and_respond_to_API(
                    mission_id
                ),
            ),
            EventHandlerMapping[RobotStatus](
                name="robot_status_event",
                event=events.robot_service_events.robot_status_update,
                handler=_robot_status_event_handler,
            ),
            EventHandlerMapping[EmptyMessage](
                name="set_maintenance_mode",
                event=events.api_requests.set_maintenance_mode.request,
                handler=lambda _: Maintenance.transition_and_reply_to_API(),
            ),
        ]
        super().__init__(
            state_name=States.UnknownStatus,
            signal_exit_event=events.signal_state_machine_exit,
            event_handler_mappings=event_handlers,
        )


def transition() -> Transition[UnknownStatus]:
    def _transition(events: Events) -> UnknownStatus:
        return UnknownStatus(events)

    return _transition
