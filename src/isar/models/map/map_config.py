from dataclasses import dataclass

from alitra import PointList


@dataclass
class MapConfig:
    map_name: str
    robot_reference_points: PointList
    asset_reference_points: PointList
