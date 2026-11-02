import logging
from time import monotonic

from robot_interface.telemetry.mqtt_client import MqttTelemetryPublisher


def stop_telemetry_publishers(
    publishers: list[MqttTelemetryPublisher], timeout: float = 5.0
) -> bool:
    for publisher in publishers:
        publisher.stop()

    deadline = monotonic() + timeout
    for publisher in publishers:
        if publisher.ident is not None:
            publisher.join(timeout=max(0.0, deadline - monotonic()))

    remaining = [publisher.name for publisher in publishers if publisher.is_alive()]
    if remaining:
        logging.getLogger("main").error(
            "Telemetry publishers did not stop within %.1f seconds: %s",
            timeout,
            ", ".join(remaining),
        )
        return False
    return True
