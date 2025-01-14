from enum import Enum


# Did you write your own isar-robot package and would like to have it included here?
# Open a pull request to the ISAR repository!
class RobotModel(Enum):
    TaurobInspector = "TaurobInspector"
    TaurobOperator = "TaurobOperator"
    ExR2 = "ExR2"
    Robot = "Robot"  # This corresponds to the mock in isar_robot
    Turtlebot = "Turtlebot"
    AnymalX = "AnymalX"
    AnymalD = "AnymalD"
