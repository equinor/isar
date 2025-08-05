from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


def trigger_pause_mission_event(state_machine: "StateMachine") -> bool:
    state_machine.events.state_machine_events.pause_mission.trigger_event(True)
    return True


# def pause_mission (state_machine: "StateMachine") -> bool:
#     state_machine.logger.info("Pausing mission: %s", state_machine.current_mission.id)

#     max_retries = settings.STATE_TRANSITION_NUM_RETIRES
#     retry_interval = settings.STATE_TRANSITION_RETRY_INTERVAL_SEC

#     for attempt in range(max_retries):
#         try:
#             state_machine.robot.pause()
#             state_machine.current_mission.status = MissionStatus.Paused
#             state_machine.current_task.status = TaskStatus.Paused

#             paused_mission_response: ControlMissionResponse = (
#                 state_machine._make_control_mission_response()
#             )
#             state_machine.events.api_requests.pause_mission.output.put(
#                 paused_mission_response
#             )

#             state_machine.publish_mission_status()
#             state_machine.publish_task_status(task=state_machine.current_task)

#             state_machine.logger.info("Mission paused successfully.")
#             return True
#         except RobotActionException as e:
#             state_machine.logger.warning(
#                 f"Attempt {attempt + 1} to pause mission failed: {e.error_description}"
#             )
#             time.sleep(retry_interval)
#         except RobotException as e:
#             state_machine.logger.warning(
#                 f"Attempt {attempt + 1} to pause mission raised a RobotException: {e.error_description}"
#             )
#             time.sleep(retry_interval)

#     state_machine.logger.error("Failed to pause mission after multiple attempts.")
#     return False
