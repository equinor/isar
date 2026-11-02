"""Verify process exit while a telemetry callback remains blocked."""

from threading import Event

from isar.models.mqtt_queue import MQTTQueue
from isar.shutdown import stop_telemetry_publishers
from robot_interface.telemetry.mqtt_client import (
    MqttTelemetryPublisher,
    TelemetryParameters,
)


def main() -> None:
    callback_started = Event()

    def blocked_callback() -> str:
        callback_started.set()
        Event().wait()
        return "{}"

    publisher = MqttTelemetryPublisher(
        MQTTQueue(), TelemetryParameters("test", blocked_callback, "pose", 0.01)
    )
    publisher.start()
    assert callback_started.wait(timeout=2)
    assert not stop_telemetry_publishers([publisher], timeout=0.05)


if __name__ == "__main__":
    main()
