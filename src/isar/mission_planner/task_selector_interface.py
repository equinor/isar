from abc import ABCMeta, abstractmethod
from typing import List

from robot_interface.models.mission.task import TASKS


class TaskSelectorInterface(metaclass=ABCMeta):
    def __init__(self) -> None:
        self.tasks: List[TASKS] = None

    def initialize(self, tasks: List[TASKS]) -> None:
        self.tasks = tasks

    @abstractmethod
    def next_task(self) -> TASKS:
        """
        Returns
        -------
        Task
            Returns the next task from the list of tasks

        Raises
        ------
        TaskSelectorStop
            If all tasks have been selected, and the task selection process is complete.
        """
        pass


class TaskSelectorStop(Exception):
    pass
