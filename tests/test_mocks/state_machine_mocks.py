from threading import Thread

from isar.modules import ApplicationContainer
from isar.robot.robot_service import RobotService
from isar.services.mission_queue.mission_queue_service import MissionQueueService
from isar.state_machine.state_machine import StateMachine


class StateMachineThreadMock:
    def __init__(self, container: ApplicationContainer) -> None:
        self.state_machine: StateMachine = container.state_machine()
        self._mission_queue_thread: MissionQueueService = MissionQueueService(
            self.state_machine.events
        )
        self._thread: Thread = Thread(
            name="State machine mock", target=self.state_machine.run
        )

    def start(self) -> None:
        self._mission_queue_thread.start()
        self._thread.start()

    def join(self) -> None:
        self.state_machine.terminate()
        self._thread.join()
        self._mission_queue_thread.join()


class RobotServiceThreadMock:
    def __init__(self, robot_service: RobotService) -> None:
        self.robot_service: RobotService = robot_service

    def start(self) -> None:
        self._thread: Thread = Thread(
            name="Robot service mock", target=self.robot_service.run
        )
        self._thread.start()

    def join(self) -> None:
        self.robot_service.stop()
        self._thread.join()
