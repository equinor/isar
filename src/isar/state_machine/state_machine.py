import json
import logging
import queue
import time
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional

from alitra import Pose
from injector import inject
from transitions import Machine
from transitions.core import State

from isar.apis.models.models import ControlMissionResponse
from isar.config.settings import settings
from isar.mission_planner.task_selector_interface import (
    TaskSelectorInterface,
    TaskSelectorStop,
)
from isar.models.communication.message import StartMissionMessage
from isar.models.communication.queues.queues import Queues
from isar.state_machine.states import (
    Idle,
    Initialize,
    Initiate,
    Monitor,
    Off,
    Paused,
    Stop,
)
from isar.state_machine.states_enum import States
from robot_interface.models.exceptions.robot_exceptions import ErrorMessage
from robot_interface.models.initialize.initialize_params import InitializeParams
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.status import MissionStatus, StepStatus, TaskStatus
from robot_interface.models.mission.step import Step
from robot_interface.models.mission.task import Task
from robot_interface.robot_interface import RobotInterface
from robot_interface.telemetry.mqtt_client import MqttClientInterface
from robot_interface.utilities.json_service import EnhancedJSONEncoder


class StateMachine(object):
    """Handles state transitions for supervisory robot control."""

    @inject
    def __init__(
        self,
        queues: Queues,
        robot: RobotInterface,
        mqtt_publisher: MqttClientInterface,
        task_selector: TaskSelectorInterface,
        sleep_time: float = settings.FSM_SLEEP_TIME,
        stepwise_mission: bool = settings.RUN_MISSION_STEPWISE,
        stop_robot_attempts_limit: int = settings.STOP_ROBOT_ATTEMPTS_LIMIT,
        transitions_log_length: int = settings.STATE_TRANSITIONS_LOG_LENGTH,
    ):
        """Initializes the state machine.

        Parameters
        ----------
        queues : Queues
            Queues used for API communication.
        robot : RobotInterface
            Instance of robot interface.
        mqtt_publisher : MqttClientInterface
            Instance of MQTT client interface which has a publish function
        sleep_time : float
            Time to sleep in between state machine iterations.
        stop_robot_attempts_limit : int
            Maximum attempts to stop the robot when stop command is received
        transitions_log_length : int
            Length of state transition log list.

        """
        self.logger = logging.getLogger("state_machine")

        self.queues: Queues = queues
        self.robot: RobotInterface = robot
        self.mqtt_publisher: Optional[MqttClientInterface] = mqtt_publisher
        self.task_selector: TaskSelectorInterface = task_selector
        self.stepwise_mission: bool = stepwise_mission

        # List of states
        self.stop_state: State = Stop(self)
        self.paused_state: State = Paused(self)
        self.idle_state: State = Idle(self)
        self.initialize_state: State = Initialize(self)
        self.monitor_state: State = Monitor(self)
        self.initiate_state: State = Initiate(self)
        self.off_state: State = Off(self)

        self.states: List[State] = [
            self.off_state,
            self.idle_state,
            self.initialize_state,
            self.initiate_state,
            self.monitor_state,
            self.stop_state,
            self.paused_state,
        ]

        self.machine = Machine(self, states=self.states, initial="off", queued=True)
        self.machine.add_transitions(
            [
                {
                    "trigger": "start_machine",
                    "source": self.off_state,
                    "dest": self.idle_state,
                    "before": self._off,
                },
                {
                    "trigger": "initiated",
                    "source": self.initiate_state,
                    "dest": self.monitor_state,
                    "before": self._initiated,
                },
                {
                    "trigger": "pause",
                    "source": [self.initiate_state, self.monitor_state],
                    "dest": self.stop_state,
                    "before": self._pause,
                },
                {
                    "trigger": "stop",
                    "source": [self.initiate_state, self.monitor_state],
                    "dest": self.stop_state,
                    "before": self._stop,
                },
                {
                    "trigger": "mission_finished",
                    "source": [
                        self.initiate_state,
                    ],
                    "dest": self.idle_state,
                    "before": self._mission_finished,
                },
                {
                    "trigger": "mission_started",
                    "source": self.idle_state,
                    "dest": self.initialize_state,
                    "before": self._mission_started,
                },
                {
                    "trigger": "initialization_successful",
                    "source": self.initialize_state,
                    "dest": self.initiate_state,
                    "before": self._initialization_successful,
                },
                {
                    "trigger": "initialization_failed",
                    "source": self.initialize_state,
                    "dest": self.idle_state,
                    "before": self._initialization_failed,
                },
                {
                    "trigger": "resume",
                    "source": self.paused_state,
                    "dest": self.initiate_state,
                    "before": self._resume,
                },
                {
                    "trigger": "step_finished",
                    "source": self.monitor_state,
                    "dest": self.initiate_state,
                    "before": self._step_finished,
                },
                {
                    "trigger": "full_mission_finished",
                    "source": self.monitor_state,
                    "dest": self.initiate_state,
                    "before": self._full_mission_finished,
                },
                {
                    "trigger": "mission_paused",
                    "source": self.stop_state,
                    "dest": self.paused_state,
                    "before": self._mission_paused,
                },
                {
                    "trigger": "initiate_infeasible",
                    "source": self.initiate_state,
                    "dest": self.initiate_state,
                    "before": self._initiate_infeasible,
                },
                {
                    "trigger": "initiate_failed",
                    "source": self.initiate_state,
                    "dest": self.idle_state,
                    "before": self._initiate_failed,
                },
                {
                    "trigger": "mission_stopped",
                    "source": [self.stop_state, self.paused_state],
                    "dest": self.idle_state,
                    "before": self._mission_stopped,
                },
            ]
        )

        self.stop_robot_attempts_limit: int = stop_robot_attempts_limit
        self.sleep_time: float = sleep_time

        self.stopped: bool = False
        self.current_mission: Optional[Mission] = None
        self.current_task: Optional[Task] = None
        self.current_step: Optional[Step] = None
        self.initial_pose: Optional[Pose] = None

        self.current_state: State = States(self.state)  # type: ignore

        self.predefined_mission_id: Optional[int] = None

        self.transitions_log_length: int = transitions_log_length
        self.transitions_list: Deque[States] = deque([], self.transitions_log_length)

    #################################################################################
    # Transition Callbacks
    def _initialization_successful(self) -> None:
        return

    def _initialization_failed(self) -> None:
        self.queues.start_mission.output.put(False)
        self._finalize()

    def _initiated(self) -> None:
        if self.stepwise_mission:
            self.current_step.status = StepStatus.InProgress
            self.publish_step_status(step=self.current_step)
            self.logger.info(
                f"Successfully initiated "
                f"{type(self.current_step).__name__} "
                f"step: {str(self.current_step.id)[:8]}"
            )
        else:
            self.current_mission.status = MissionStatus.InProgress
            self.logger.info(
                f"Successfully initiated full mission with ID: "
                f"{str(self.current_mission.id)[:8]}"
            )

    def _pause(self) -> None:
        return

    def _off(self) -> None:
        return

    def _resume(self) -> None:
        self.logger.info(f"Resuming mission: {self.current_mission.id}")
        self.current_mission.status = MissionStatus.InProgress
        self.current_mission.error_message = None
        self.current_task.status = TaskStatus.InProgress

        self.publish_mission_status()
        self.publish_task_status(task=self.current_task)

        resume_mission_response: ControlMissionResponse = (
            self._make_control_mission_response()
        )
        self.queues.resume_mission.output.put(resume_mission_response)

        self.current_task.reset_task()
        self.update_current_step()

    def _mission_finished(self) -> None:
        fail_statuses: List[TaskStatus] = [
            TaskStatus.Cancelled,
            TaskStatus.Failed,
        ]
        partially_fail_statuses = fail_statuses + [TaskStatus.PartiallySuccessful]

        if all(task.status in fail_statuses for task in self.current_mission.tasks):
            self.current_mission.error_message = ErrorMessage(
                error_reason=None,
                error_description="The mission failed because all tasks in the mission "
                "failed",
            )
            self.current_mission.status = MissionStatus.Failed
        elif any(
            task.status in partially_fail_statuses
            for task in self.current_mission.tasks
        ):
            self.current_mission.status = MissionStatus.PartiallySuccessful
        else:
            self.current_mission.status = MissionStatus.Successful
        self._finalize()

    def _mission_started(self) -> None:
        self.queues.start_mission.output.put(True)
        self.logger.info(
            f"Initialization successful. Starting new mission: "
            f"{self.current_mission.id}"
        )
        self.log_step_overview(mission=self.current_mission)

        self.current_mission.status = MissionStatus.InProgress
        self.publish_mission_status()
        self.current_task = self.task_selector.next_task()
        self.current_task.status = TaskStatus.InProgress
        self.publish_task_status(task=self.current_task)
        self.update_current_step()

    def _step_finished(self) -> None:
        self.publish_step_status(step=self.current_step)
        self.update_current_task()
        self.update_current_step()

    def _full_mission_finished(self) -> None:
        self.current_task = None
        step_status: StepStatus = StepStatus.Failed
        task_status: TaskStatus = TaskStatus.Failed

        if self.current_mission.status == MissionStatus.Failed:
            step_status = StepStatus.Failed
            task_status = TaskStatus.Failed
        elif self.current_mission.status == MissionStatus.Cancelled:
            step_status = StepStatus.Cancelled
            task_status = TaskStatus.Cancelled
        elif (
            self.current_mission.status == MissionStatus.Successful
            or self.current_mission.status == MissionStatus.PartiallySuccessful
        ):
            step_status = StepStatus.Successful
            task_status = TaskStatus.Successful

        for task in self.current_mission.tasks:
            task.status = task_status
            for step in task.steps:
                step.status = step_status
                self.publish_step_status(step=step)
            self.publish_task_status(task=task)

    def _mission_paused(self) -> None:
        self.logger.info(f"Pausing mission: {self.current_mission.id}")
        self.current_mission.status = MissionStatus.Paused
        self.current_task.status = TaskStatus.Paused
        self.current_step.status = StepStatus.NotStarted

        paused_mission_response: ControlMissionResponse = (
            self._make_control_mission_response()
        )
        self.queues.pause_mission.output.put(paused_mission_response)

        self.publish_mission_status()
        self.publish_task_status(task=self.current_task)
        self.publish_step_status(step=self.current_step)

    def _stop(self) -> None:
        self.stopped = True

    def _initiate_failed(self) -> None:
        self.current_step.status = StepStatus.Failed
        self.current_task.update_task_status()
        self.current_mission.status = MissionStatus.Failed
        self.publish_step_status(step=self.current_step)
        self.publish_task_status(task=self.current_task)
        self._finalize()

    def _initiate_infeasible(self) -> None:
        if self.stepwise_mission:
            self.current_step.status = StepStatus.Failed
            self.publish_step_status(step=self.current_step)
            self.update_current_task()
            self.update_current_step()

    def _mission_stopped(self) -> None:
        self.current_mission.status = MissionStatus.Cancelled

        for task in self.current_mission.tasks:
            for step in task.steps:
                if step.status in [StepStatus.NotStarted, StepStatus.InProgress]:
                    step.status = StepStatus.Cancelled
            if task.status in [
                TaskStatus.NotStarted,
                TaskStatus.InProgress,
                TaskStatus.Paused,
            ]:
                task.status = TaskStatus.Cancelled

        stopped_mission_response: ControlMissionResponse = (
            self._make_control_mission_response()
        )
        self.queues.stop_mission.output.put(stopped_mission_response)

        self.publish_task_status(task=self.current_task)
        self.publish_step_status(step=self.current_step)
        self._finalize()

    #################################################################################

    def _finalize(self) -> None:
        self.publish_mission_status()
        self.log_step_overview(mission=self.current_mission)
        state_transitions: str = ", ".join(
            [
                f"\n  {transition}" if (i + 1) % 10 == 0 else f"{transition}"
                for i, transition in enumerate(list(self.transitions_list))
            ]
        )
        self.logger.info(f"State transitions:\n  {state_transitions}")
        self.reset_state_machine()

    def begin(self):
        """Starts the state machine.

        Transitions into idle state.

        """
        self.to_idle()

    def update_current_task(self):
        if self.current_task.is_finished():
            self.current_task.update_task_status()
            self.publish_task_status(task=self.current_task)
            try:
                self.current_task = self.task_selector.next_task()
                self.current_task.status = TaskStatus.InProgress
                self.publish_task_status(task=self.current_task)
            except TaskSelectorStop:
                # Indicates that all tasks are finished
                self.current_task = None

    def update_current_step(self):
        if self.current_task:
            self.current_step = self.current_task.next_step()

    def update_state(self):
        """Updates the current state of the state machine."""
        self.current_state = States(self.state)
        self.send_state_status()
        self._log_state_transition(self.current_state)
        self.logger.info(f"State: {self.current_state}")
        self.publish_state()

    def reset_state_machine(self) -> None:
        self.logger.info("Resetting state machine")
        self.stopped = False
        self.current_step = None
        self.current_task = None
        self.current_mission = None
        self.initial_pose = None

    def start_mission(self, mission: Mission, initial_pose: Pose):
        """Starts a scheduled mission."""
        self.current_mission = mission
        self.initial_pose = initial_pose

        self.task_selector.initialize(tasks=self.current_mission.tasks)

    def get_initialize_params(self):
        return InitializeParams(initial_pose=self.initial_pose)

    def should_start_mission(self) -> Optional[StartMissionMessage]:
        try:
            return self.queues.start_mission.input.get(block=False)
        except queue.Empty:
            return None

    def should_stop_mission(self) -> bool:
        try:
            return self.queues.stop_mission.input.get(block=False)
        except queue.Empty:
            return False

    def should_pause_mission(self) -> bool:
        try:
            return self.queues.pause_mission.input.get(block=False)
        except queue.Empty:
            return False

    def should_resume_mission(self) -> bool:
        try:
            return self.queues.resume_mission.input.get(block=False)
        except queue.Empty:
            return False

    def send_state_status(self):
        self.queues.state.update(self.current_state)

    def publish_mission_status(self) -> None:
        if not self.mqtt_publisher:
            return

        error_message: Optional[ErrorMessage] = None
        if self.current_mission:
            if self.current_mission.error_message:
                error_message = self.current_mission.error_message
        payload: str = json.dumps(
            {
                "isar_id": settings.ISAR_ID,
                "robot_name": settings.ROBOT_NAME,
                "mission_id": self.current_mission.id if self.current_mission else None,
                "status": self.current_mission.status if self.current_mission else None,
                "error_reason": error_message.error_reason if error_message else None,
                "error_description": (
                    error_message.error_description if error_message else None
                ),
                "timestamp": datetime.utcnow(),
            },
            cls=EnhancedJSONEncoder,
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_MISSION,
            payload=payload,
            retain=False,
        )

    def publish_task_status(self, task: Task) -> None:
        """Publishes the task status to the MQTT Broker"""
        if not self.mqtt_publisher:
            return

        error_message: Optional[ErrorMessage] = None
        if task:
            if task.error_message:
                error_message = task.error_message

        payload: str = json.dumps(
            {
                "isar_id": settings.ISAR_ID,
                "robot_name": settings.ROBOT_NAME,
                "mission_id": self.current_mission.id if self.current_mission else None,
                "task_id": task.id if task else None,
                "status": task.status if task else None,
                "error_reason": error_message.error_reason if error_message else None,
                "error_description": (
                    error_message.error_description if error_message else None
                ),
                "timestamp": datetime.utcnow(),
            },
            cls=EnhancedJSONEncoder,
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_TASK,
            payload=payload,
            retain=False,
        )

    def publish_step_status(self, step: Step) -> None:
        """Publishes the step status to the MQTT Broker"""
        if not self.mqtt_publisher:
            return

        error_message: Optional[ErrorMessage] = None
        if step:
            if step.error_message:
                error_message = step.error_message

        payload: str = json.dumps(
            {
                "isar_id": settings.ISAR_ID,
                "robot_name": settings.ROBOT_NAME,
                "mission_id": self.current_mission.id if self.current_mission else None,
                "task_id": self.current_task.id if self.current_task else None,
                "step_id": step.id if step else None,
                "step_type": step.__class__.__name__ if step else None,
                "status": step.status if step else None,
                "error_reason": error_message.error_reason if error_message else None,
                "error_description": (
                    error_message.error_description if error_message else None
                ),
                "timestamp": datetime.utcnow(),
            },
            cls=EnhancedJSONEncoder,
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_STEP,
            payload=payload,
            retain=False,
        )

    def publish_state(self) -> None:
        if not self.mqtt_publisher:
            return
        payload: str = json.dumps(
            {
                "isar_id": settings.ISAR_ID,
                "robot_name": settings.ROBOT_NAME,
                "state": self.current_state,
                "timestamp": datetime.utcnow(),
            },
            cls=EnhancedJSONEncoder,
        )

        self.mqtt_publisher.publish(
            topic=settings.TOPIC_ISAR_STATE,
            payload=payload,
            retain=False,
        )

    def _log_state_transition(self, next_state):
        """Logs all state transitions that are not self-transitions."""
        self.transitions_list.append(next_state)

    def log_step_overview(self, mission: Mission):
        """Log an overview of the steps in a mission"""
        log_statements: List[str] = []
        for task in mission.tasks:
            log_statements.append(
                f"{type(task).__name__:<20} {str(task.id)[:8]:<32} -- {task.status}"
            )
            for j, step in enumerate(task.steps):
                log_statements.append(
                    f"{j:>3} {type(step).__name__:<20} {str(step.id)[:8]:<32} -- {step.status}"  # noqa: E501
                )

        log_statement: str = "\n".join(log_statements)

        self.logger.info(f"Mission overview:\n{log_statement}")

    def _make_control_mission_response(self) -> ControlMissionResponse:
        return ControlMissionResponse(
            mission_id=self.current_mission.id,
            mission_status=self.current_mission.status,
            task_id=self.current_task.id,
            task_status=self.current_task.status,
            step_id=self.current_step.id,
            step_status=self.current_step.status,
        )


def main(state_machine: StateMachine):
    """Starts a state machine instance."""
    state_machine.begin()
