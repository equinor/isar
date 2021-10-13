from enum import Enum


class Frame(str, Enum):
    """
    Robot frame implies the local frame on the operating robot. This will depend on the robots internal mapping.
    Asset frame is the frame of the asset which the robot operates in.
    """

    Robot = "robot"
    Asset = "asset"
