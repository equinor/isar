from enum import Enum


# Did you write your own isar-robot package and would like to have it included here?
# Open a pull request to the ISAR repository!
class RobotModel(Enum):
    TaurobInspector: str = "TaurobInspector"
    TaurobOperator: str = "TaurobOperator"
    ExR2: str = "ExR2"
    Robot: str = "Robot"  # This corresponds to the mock in isar_robot
    Turtlebot: str = "Turtlebot"
    AnymalX: str = "AnymalX"
    AnymalD: str = "AnymalD"
