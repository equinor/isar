import json
from typing import Any

import pytest

from isar.models.communication.messages import StartMessage, StopMessage
from isar.services.utilities.json_service import EnhancedJSONEncoder, JsonService
from tests.mocks.status import mock_status


class TestJsonService:
    @pytest.mark.parametrize(
        "original_object",
        [
            StartMessage(message="help", started=False),
            StopMessage(message="Yes, sir!", stopped=True),
        ],
    )
    def test_dataclass_to_object(self, original_object: Any):
        json_string: str = json.dumps(original_object, cls=EnhancedJSONEncoder)
        as_object: Any = JsonService.to_object(json_string)
        assert as_object is not None

    @pytest.mark.parametrize(
        "original_object",
        [mock_status()],
    )
    def test_to_object(self, original_object: Any):
        json_string: str = json.dumps(original_object, cls=EnhancedJSONEncoder)
        as_object: Any = JsonService.to_object(json_string)
        assert as_object is not None
