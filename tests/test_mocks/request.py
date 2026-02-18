from typing import Any


class StubRequests:
    def __init__(self, json_data: Any | None = None) -> None:
        self.json_data = json_data

    def json(self) -> Any | None:
        return self.json_data
