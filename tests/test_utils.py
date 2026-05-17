import time
from collections.abc import Callable


def wait_until(
    condition: Callable[[], bool],
    timeout: float = 5,
    interval: float = 0.01,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(interval)
    return condition()
