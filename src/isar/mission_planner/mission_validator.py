from typing import List

from isar.models.mission import Mission


def is_robot_capable_of_mission(
    mission: Mission, robot_capabilities: List[str]
) -> bool:
    return all(
        [
            step.type in robot_capabilities
            for task in mission.tasks
            for step in task.steps
        ]
    )
