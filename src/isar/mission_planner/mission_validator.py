from typing import List, Tuple

from isar.models.mission import Mission


def is_robot_capable_of_mission(
    mission: Mission, robot_capabilities: List[str]
) -> Tuple[bool, List[str]]:
    success: bool = True
    missing_capabilities: List[str] = []
    for task in mission.tasks:
        for step in task.steps:
            if not step.type in robot_capabilities:
                success = False
                missing_capabilities.append(step.type)

    return success, missing_capabilities
