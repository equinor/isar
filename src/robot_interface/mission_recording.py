"""Optional mission recording boundary; transport and camera ownership stay in drivers."""

from abc import ABC, abstractmethod


class MissionRecorder(ABC):
    @abstractmethod
    def start(self, mission_id: str) -> None:
        """Schedule capture without blocking robot execution; repeated starts are safe."""

    @abstractmethod
    def stop(self, mission_id: str, interrupted: bool = False) -> None:
        """Request recording to stop without blocking robot execution."""

    @abstractmethod
    def close(self) -> None:
        """Release recording resources within a bounded shutdown period."""
