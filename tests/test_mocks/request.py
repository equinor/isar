from typing import Any, Optional


class StubRequests:
    def __init__(self, json_data: Optional[Any] = None) -> None:
        self.json_data = json_data

    def json(self) -> Optional[Any]:
        return self.json_data
