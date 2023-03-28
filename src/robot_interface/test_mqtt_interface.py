from alitra import Pose, Position, Orientation, Frame
from datetime import datetime
from robot_interface.telemetry.payloads import (
    TelemetryPosePayload,
    TelemetryBatteryPayload,
    TelemetryPressurePayload,
)


def recursivly_compare_attributes(object1, object2):
    attributes_object1 = [
        attribute
        for attribute in dir(object1)
        if not (attribute.startswith("__") or callable(getattr(object1, attribute)))
    ]
    attributes_object2 = [
        attribute
        for attribute in dir(object2)
        if not (attribute.startswith("__") or callable(getattr(object2, attribute)))
    ]

    assert len(attributes_object1) == len(attributes_object2)

    for attribute in attributes_object1:
        assert attribute in attributes_object2

        next_object = getattr(object1, attribute)
        if not (
            isinstance(next_object, int)
            or isinstance(next_object, float)
            or isinstance(next_object, datetime)
        ):
            recursivly_compare_attributes(
                getattr(object1, attribute), getattr(object2, attribute)
            )


def mqtt_interface_test(
    robot_pose_telemetry_payload: TelemetryPosePayload,
    robot_battery_telemetry_payload: TelemetryBatteryPayload,
    robot_pressure_telemetry_payload: TelemetryPressurePayload,
) -> None:
    isar_pose_telemetry_payload = TelemetryPosePayload(
        isar_id="default",
        robot_name="default",
        timestamp=datetime.utcnow(),
        pose=Pose(
            position=Position(1, 1, 1, Frame(name="asset")),
            orientation=Orientation(0, 0, 0, 1, Frame(name="asset")),
            frame=Frame(name="asset"),
        ),
    )

    isar_battery_telemetry_payload = TelemetryBatteryPayload(
        isar_id="default",
        robot_name="default",
        timestamp=datetime.utcnow(),
        battery_level=1.1,
    )

    isar_pressure_telemetry_payload = TelemetryPressurePayload(
        isar_id="default",
        robot_name="default",
        timestamp=datetime.utcnow(),
        pressure_level=1.1,
    )

    recursivly_compare_attributes(
        robot_pose_telemetry_payload, isar_pose_telemetry_payload
    )

    recursivly_compare_attributes(
        robot_battery_telemetry_payload, isar_battery_telemetry_payload
    )

    recursivly_compare_attributes(
        robot_pressure_telemetry_payload, isar_pressure_telemetry_payload
    )
