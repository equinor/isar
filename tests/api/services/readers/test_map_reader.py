import logging
from pathlib import Path

import pytest
from alitra.frame_dataclasses import Point, PointList

from isar.models.map.map_config import MapConfig

logger = logging.getLogger("state_machine")


expected_map_config = MapConfig(
    map_name="test_map",
    robot_reference_points=PointList(
        points=[
            Point(x=10, y=20, z=30, frame="robot"),
            Point(x=40, y=50, z=60, frame="robot"),
            Point(x=70, y=80, z=90, frame="robot"),
        ],
        frame="robot",
    ),
    asset_reference_points=PointList(
        points=[
            Point(x=11, y=21, z=31, frame="asset"),
            Point(x=41, y=51, z=61, frame="asset"),
            Point(x=71, y=81, z=91, frame="asset"),
        ],
        frame="asset",
    ),
)


def test_map_config_reader(map_config_reader):
    map_config_path = Path("./tests/test_data/test_map_config/test_map_config.json")
    map_config = map_config_reader.get_map_config(map_config_path)
    assert map_config == expected_map_config


def test_invalid_file_path(map_config_reader):
    map_config_path = Path("./tests/test_data/test_map_config/no_file.json")
    with pytest.raises(Exception):
        map_config_reader.get_map_config(map_config_path)


def test_get_map_config_by_name(map_config_reader):
    map_config_reader.predefined_map_config_folder = Path(
        "./tests/test_data/test_map_config"
    )
    map_config = map_config_reader.get_map_config_by_name("test_map")
    assert map_config == expected_map_config


def test_handle_map_config_by_name_not_found(caplog, map_config_reader):
    map_config_reader.predefined_map_config_folder = Path(
        "./tests/test_data/test_map_config"
    )
    map_config = map_config_reader.get_map_config_by_name("non_existing_test_map")
    assert map_config == None
