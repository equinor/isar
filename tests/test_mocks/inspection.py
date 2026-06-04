from datetime import datetime

from alitra import Frame, Orientation, Pose, Position

from robot_interface.models.inspection.inspection import (
    AcousticMeasurementMetadata,
    ImageMetadata,
)


def stub_pose() -> Pose:
    return Pose(
        position=Position(x=0, y=0, z=0, frame=Frame("asset")),
        orientation=Orientation(x=0, y=0, z=0, w=1, frame=Frame("asset")),
        frame=Frame("asset"),
    )


def stub_image_metadata(
    analysis_types: list[str] | None = None,
) -> ImageMetadata:
    return ImageMetadata(
        start_time=datetime.now(),
        robot_pose=stub_pose(),
        target_position=Position(x=0, y=0, z=0, frame=Frame("asset")),
        file_type="jpg",
        analysis_types=analysis_types,
    )


def stub_acoustic_measurement_metadata() -> AcousticMeasurementMetadata:
    return AcousticMeasurementMetadata(
        start_time=datetime.now(),
        robot_pose=stub_pose(),
        target_position=Position(x=0, y=0, z=0, frame=Frame("asset")),
        file_type="mp4",
        duration=2.995,
        snr_value=87.5,
        leak_rate=0.55,
        leak_rate_unit="l/min",
        sound_pressure_level_at_sensor_db=0.0,
        sound_pressure_level_at_source_db=36.7,
        distance_to_source=0.3,
        result="RI_ANOMALY",
        frequency_from=35000.0,
        frequency_to=40000.0,
    )
