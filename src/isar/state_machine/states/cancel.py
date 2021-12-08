import logging
from typing import TYPE_CHECKING, Optional

from injector import inject
from transitions import State

from isar.storage.storage_service import StorageService
from robot_interface.models.inspection.inspection import InspectionResult

if TYPE_CHECKING:
    from isar.state_machine.state_machine import StateMachine


class Cancel(State):
    @inject
    def __init__(
        self,
        state_machine: "StateMachine",
        storage_service: StorageService,
    ):
        super().__init__(name="cancel", on_enter=self.start, on_exit=self.stop)
        self.state_machine: "StateMachine" = state_machine
        self.storage_service = storage_service
        self.logger = logging.getLogger("state_machine")

    def start(self):
        self.state_machine.update_status()
        self.logger.info(f"State: {self.state_machine.status.current_state}")

        if self.state_machine.status.scheduled_mission.inspections:
            for (
                inspection_ref
            ) in self.state_machine.status.scheduled_mission.inspections:
                result: Optional[
                    InspectionResult
                ] = self.state_machine.robot.download_inspection_result(inspection_ref)
                if result:
                    self.storage_service.store(
                        self.state_machine.status.scheduled_mission.id,
                        result,
                    )
                else:
                    self.logger.warning(
                        f"Failed to upload inspection result as no result was received. "
                        + f"Inspection reference: {inspection_ref}"
                    )

            self.storage_service.store_metadata(
                self.state_machine.status.scheduled_mission
            )

        next_state = self.state_machine.reset_state_machine()
        self.state_machine.to_next_state(next_state)

    def stop(self):
        self._log_state_transitions()

    def _log_state_transitions(self):
        state_transitions: str = ", ".join(
            [
                f"\n  {transition}" if (i + 1) % 10 == 0 else f"{transition}"
                for i, transition in enumerate(
                    list(self.state_machine.transitions_list)
                )
            ]
        )

        self.logger.info(f"State transitions:\n  {state_transitions}")
