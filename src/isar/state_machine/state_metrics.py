from typing import Callable, List

from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Meter, Observation

from isar.config.settings import settings
from isar.state_machine.states_enum import STATE_TO_CODE, States

UNKNOWN_STATE_CODE: int = -1


class StateMetricsPublisher:
    def __init__(self, current_state_provider: Callable[[], States]) -> None:
        self._current_state_provider = current_state_provider

        self.meter: Meter = metrics.get_meter("isar.state_machine")
        self.meter.create_observable_gauge(
            name="isar.state",
            callbacks=[self._observe_state],
            description="Current state of the ISAR state machine (see STATE_TO_CODE)",
        )

    def _observe_state(self, _: CallbackOptions) -> List[Observation]:
        state: States = self._current_state_provider()
        code: int = STATE_TO_CODE.get(state, UNKNOWN_STATE_CODE)
        return [
            Observation(
                value=code,
                attributes={
                    "robot_name": settings.ROBOT_NAME,
                    "isar_id": settings.ISAR_ID,
                },
            )
        ]
