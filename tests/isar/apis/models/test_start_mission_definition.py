from pathlib import Path

import pytest
from alitra import Frame, Orientation, Pose, Position
from pydantic import ValidationError

from isar.apis.models.start_mission_definition import (
    InspectionTypes,
    MissionFormatError,
    StartMissionDefinition,
    StartMissionTaskDefinition,
    to_isar_mission,
)
from robot_interface.models.mission.mission import Mission
from robot_interface.models.mission.task import (
    InspectionTask,
    Roi,
    TakeAcousticMeasurement,
    TakeImage,
)
from tests.test_mocks.mission_definition import DummyMissionDefinition


@pytest.mark.parametrize("from_json", [False, True], ids=["model", "json"])
def test_image_mission_conversion(from_json: bool) -> None:
    task_pose = Pose(
        position=Position(x=1, y=1, z=1, frame=Frame("robot")),
        orientation=Orientation(x=1, y=1, z=1, w=1, frame=Frame("robot")),
        frame=Frame("robot"),
    )
    task_definition = StartMissionTaskDefinition(
        id="test-id",
        pose=task_pose,
        type=InspectionTypes.image,
        inspection_target=Position(x=1, y=1, z=1, frame=Frame("robot")),
    )
    mission_definition = StartMissionDefinition(
        tasks=[task_definition], name="mission_name", id="test-id2"
    )
    expected = Mission(
        id="test-id2",
        name="mission_name",
        tasks=[
            TakeImage(id="test-id", robot_pose=task_pose, target=task_pose.position)
        ],
    )
    if from_json:
        path = Path(__file__).with_name("example_mission_definition.json")
        mission_definition = StartMissionDefinition.model_validate_json(
            path.read_text()
        )
        expected_pose = Pose(
            position=Position(0.0, 0.0, 0.0, frame=Frame("robot")),
            orientation=Orientation(0.0, 0.0, 0.0, 0.0, frame=Frame("robot")),
            frame=Frame("robot"),
        )
        expected = Mission(
            id="generated_mission_id",
            name="my-mission",
            tasks=[
                TakeImage(
                    id="generated_task_id",
                    robot_pose=expected_pose,
                    target=expected_pose.position,
                    analysis_types=["anonymize"],
                    tag_id="MY-TAG-123",
                )
            ],
        )

    mission = to_isar_mission(mission_definition)

    assert mission == expected


def _build_mission_with_inspection_payload(inspection_payload: dict) -> Mission:
    payload = {
        "id": "dummy_mission_id",
        "name": "mission",
        "tasks": [
            {
                "id": "dummy_id",
                "type": "inspection",
                "pose": {
                    "position": {"x": 0, "y": 0, "z": 0, "frame": {"name": "robot"}},
                    "orientation": {
                        "x": 0,
                        "y": 0,
                        "z": 0,
                        "w": 1,
                        "frame": {"name": "robot"},
                    },
                    "frame": {"name": "robot"},
                },
                **inspection_payload,
            }
        ],
    }
    return to_isar_mission(StartMissionDefinition.model_validate(payload))


@pytest.mark.parametrize(
    "inspection_type",
    [t.value for t in InspectionTypes],
)
def test_analysis_types_defaults_to_none_for_all_inspection_types(
    inspection_type: str,
) -> None:
    payload: dict = {
        "type": inspection_type,
        "inspection_target": {"x": 0, "y": 0, "z": 0, "frame": {"name": "robot"}},
    }
    if inspection_type in {"Video", "ThermalVideo", "Audio"}:
        payload["duration"] = 1.0
    if inspection_type == "AcousticMeasurement":
        payload["acoustic"] = {
            "frequency_from": 35000.0,
            "frequency_to": 40000.0,
            "snr_value_threshold": 30.0,
            "detection_type": "leak",
        }

    mission = _build_mission_with_inspection_payload(payload)
    task = mission.tasks[0]
    assert isinstance(task, InspectionTask)
    assert task.analysis_types is None


def _acoustic_payload(roi: dict | None = None) -> dict:
    payload: dict = {
        "type": "AcousticMeasurement",
        "inspection_target": {"x": 0, "y": 0, "z": 0, "frame": {"name": "robot"}},
        "acoustic": {
            "frequency_from": 35000.0,
            "frequency_to": 40000.0,
            "snr_value_threshold": 30.0,
            "detection_type": "leak",
        },
    }
    if roi is not None:
        payload["acoustic"]["roi"] = roi
    return payload


@pytest.mark.parametrize(
    "roi",
    [None, Roi(x=760, y=400, width=133, height=160)],
    ids=["omitted", "specified"],
)
def test_acoustic_measurement_forwards_roi(roi: Roi | None) -> None:
    payload = _acoustic_payload(roi.model_dump() if roi is not None else None)

    mission = _build_mission_with_inspection_payload(payload)

    task = mission.tasks[0]
    assert isinstance(task, TakeAcousticMeasurement)
    assert task.roi == roi


# A malformed mission is the caller's mistake, so it must surface as
# MissionFormatError, which the scheduling controller answers with 400. A bare
# ValueError escapes that handler and becomes an opaque 500.
@pytest.mark.parametrize("inspection_type", ["Video", "AcousticMeasurement"])
def test_missing_inspection_parameters_is_a_mission_format_error(
    inspection_type: str,
) -> None:
    payload = {
        "type": inspection_type,
        "inspection_target": {"x": 0, "y": 0, "z": 0, "frame": {"name": "robot"}},
    }

    with pytest.raises(MissionFormatError):
        _build_mission_with_inspection_payload(payload)


def test_stored_mission_preserves_reference_and_execution_id() -> None:
    definition = StartMissionDefinition(
        id="execution-id",
        name="Weekly diagnostic",
        robot_mission_id="DiagnosticRoutine",
    )

    mission = to_isar_mission(definition)

    assert mission == Mission(
        id="execution-id",
        name="Weekly diagnostic",
        robot_mission_id="DiagnosticRoutine",
        tasks=[],
    )


def test_stored_mission_survives_json_round_trip() -> None:
    mission = Mission(
        id="execution-id",
        name="Weekly diagnostic",
        robot_mission_id="DiagnosticRoutine",
    )

    restored = Mission.model_validate_json(mission.model_dump_json())

    assert restored == mission


def test_robot_interface_rejects_stored_mission_with_tasks() -> None:
    with pytest.raises(ValidationError, match="cannot contain inspection tasks"):
        Mission(
            id="id",
            name="name",
            robot_mission_id="DiagnosticRoutine",
            tasks=DummyMissionDefinition.default_mission.tasks,
        )
