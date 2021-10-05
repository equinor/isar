import pytest

from isar.config import config


class TestConfig:
    @pytest.mark.parametrize(
        "expected_sections",
        [
            [
                "environment",
                "network",
                "test",
                "azure",
                "robot_api",
                "mission",
                "metadata",
                "api_namespaces",
                "stid",
                "echo",
                "logging",
                "maps",
                "auth",
            ]
        ],
    )
    def test_load_config(self, expected_sections):
        assert config.sections() == expected_sections
