import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from threading import Event

from isar.models.mqtt_queue import MQTTQueue
from isar.shutdown import stop_telemetry_publishers
from robot_interface.telemetry.mqtt_client import (
    MqttTelemetryPublisher,
    TelemetryParameters,
)


def test_stop_interrupts_long_publish_interval() -> None:
    publisher = MqttTelemetryPublisher(
        MQTTQueue(), TelemetryParameters("test", lambda: "{}", "pose", 60)
    )
    publisher.start()
    try:
        assert stop_telemetry_publishers([publisher], timeout=1)
        assert not publisher.is_alive()
    finally:
        publisher.stop()
        publisher.join(timeout=1)


def test_blocked_callback_is_reported_and_cannot_publish_after_stop() -> None:
    callback_started = Event()
    release_callback = Event()
    queue = MQTTQueue()

    def blocked_callback() -> str:
        callback_started.set()
        release_callback.wait()
        return "{}"

    publisher = MqttTelemetryPublisher(
        queue, TelemetryParameters("test", blocked_callback, "pose", 0.01)
    )
    publisher.start()
    try:
        assert callback_started.wait(timeout=2)
        assert not stop_telemetry_publishers([publisher], timeout=0.05)
        release_callback.set()
        publisher.join(timeout=1)
        assert not publisher.is_alive()
        assert queue.empty()
    finally:
        publisher.stop()
        release_callback.set()
        publisher.join(timeout=1)


def test_blocked_callback_cannot_keep_process_alive() -> None:
    code = dedent("""
        from threading import Event
        from isar.models.mqtt_queue import MQTTQueue
        from isar.shutdown import stop_telemetry_publishers
        from robot_interface.telemetry.mqtt_client import MqttTelemetryPublisher, TelemetryParameters

        started = Event()
        def blocked_callback():
            started.set()
            Event().wait()
            return "{}"

        publisher = MqttTelemetryPublisher(
            MQTTQueue(), TelemetryParameters("test", blocked_callback, "pose", 0.01)
        )
        publisher.start()
        assert started.wait(timeout=2)
        assert not stop_telemetry_publishers([publisher], timeout=0.05)
    """)
    source = Path(__file__).resolve().parents[3] / "src"
    subprocess.run(
        [sys.executable, "-c", code],
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [str(source), os.environ.get("PYTHONPATH", "")]
            ),
        },
        check=True,
        timeout=10,
    )
