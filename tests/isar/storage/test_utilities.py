import json

from isar.storage.utilities import construct_metadata_file
from robot_interface.models.inspection.inspection import AcousticMeasurement, Image
from robot_interface.models.mission.mission import Mission
from tests.test_mocks.inspection import (
    stub_acoustic_measurement_metadata,
    stub_image_metadata,
)


def test_construct_metadata_file_acoustic_includes_result_block() -> None:
    inspection = AcousticMeasurement(
        id="acoustic-1", metadata=stub_acoustic_measurement_metadata()
    )

    raw = construct_metadata_file(
        inspection=inspection, mission=Mission(name="m", tasks=[]), filename="f"
    )
    data = json.loads(raw)

    assert data["additional_meta"]["acoustic_result"] == {
        "snr_value": 87.5,
        "leak_rate": 0.55,
        "leak_rate_unit": "l/min",
        "sound_pressure_level_at_sensor_db": 0.0,
        "sound_pressure_level_at_source_db": 36.7,
        "distance_to_source": 0.3,
        "result": "RI_ANOMALY",
        "frequency_from": 35000.0,
        "frequency_to": 40000.0,
    }


def test_construct_metadata_file_non_acoustic_excludes_acoustic_result() -> None:
    inspection = Image(id="image-1", metadata=stub_image_metadata())

    raw = construct_metadata_file(
        inspection=inspection, mission=Mission(name="m", tasks=[]), filename="f"
    )
    data = json.loads(raw)

    assert "acoustic_result" not in data["additional_meta"]
