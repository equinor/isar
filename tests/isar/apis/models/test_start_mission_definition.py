import json
import os

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


def test_to_isar_mission() -> None:
    DUMMY_MISSION_NAME = "mission_name"

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
        tasks=[task_definition], name=DUMMY_MISSION_NAME, id="test-id2"
    )

    isar_mission: Mission = to_isar_mission(mission_definition)

    assert len(isar_mission.id) > 1
    assert isar_mission.name == DUMMY_MISSION_NAME
    assert len(isar_mission.tasks) == 1

    first_task = isar_mission.tasks[0]
    assert len(first_task.id) > 1

    assert isinstance(first_task, TakeImage)

    assert first_task.target == Position(x=1, y=1, z=1, frame=Frame(name="robot"))
    assert len(first_task.id) > 1
    assert first_task.robot_pose == Pose(
        position=Position(x=1, y=1, z=1, frame=Frame(name="robot")),
        orientation=Orientation(x=1, y=1, z=1, w=1, frame=Frame(name="robot")),
        frame=Frame(name="robot"),
    )


def test_mission_definition_from_json_to_isar_mission() -> None:
    dirname = os.path.dirname(__file__)
    filepath = os.path.join(dirname, "example_mission_definition.json")

    with open(filepath) as f:
        datax = json.load(f)
        mission_definition = StartMissionDefinition(**datax)

    isar_mission: Mission = to_isar_mission(mission_definition)
    assert len(isar_mission.id) > 1
    assert isar_mission.name == "my-mission"

    assert len(isar_mission.tasks) == 1
    task = isar_mission.tasks[0]
    assert len(task.id) > 1
    assert isinstance(task, TakeImage)
    assert task.robot_pose == Pose(
        position=Position(0.0, 0.0, 0.0, frame=Frame("robot")),
        orientation=Orientation(0.0, 0.0, 0.0, 0.0, frame=Frame("robot")),
        frame=Frame("robot"),
    )
    assert task.type == "take_image"
    assert task.target == Position(0.0, 0.0, 0.0, frame=Frame("robot"))
    assert task.analysis_types == ["anonymize"]


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


def test_acoustic_measurement_defaults_roi_to_none() -> None:
    mission = _build_mission_with_inspection_payload(_acoustic_payload())
    task = mission.tasks[0]
    assert isinstance(task, TakeAcousticMeasurement)
    assert task.roi is None


def test_acoustic_measurement_forwards_roi_to_task() -> None:
    mission = _build_mission_with_inspection_payload(
        _acoustic_payload(
            roi={"x": 760, "y": 400, "width": 133, "height": 160},
        )
    )
    task = mission.tasks[0]
    assert isinstance(task, TakeAcousticMeasurement)
    assert task.roi == Roi(x=760, y=400, width=133, height=160)


# A malformed mission is the caller's mistake, so it must surface as
# MissionFormatError, which the scheduling controller answers with 400. A bare
# ValueError escapes that handler and becomes an opaque 500.
def test_missing_duration_is_a_mission_format_error() -> None:
    # Video inspections require a duration.
    payload = {
        "type": "Video",
        "inspection_target": {"x": 0, "y": 0, "z": 0, "frame": {"name": "robot"}},
    }

    with pytest.raises(MissionFormatError):
        _build_mission_with_inspection_payload(payload)


def test_missing_acoustic_parameters_is_a_mission_format_error() -> None:
    payload = {
        "type": "AcousticMeasurement",
        "inspection_target": {"x": 0, "y": 0, "z": 0, "frame": {"name": "robot"}},
    }

    with pytest.raises(MissionFormatError):
        _build_mission_with_inspection_payload(payload)


def test_stored_mission_preserves_reference_and_execution_id() -> None:
    mission = to_isar_mission(
        StartMissionDefinition(
            id="execution-id",
            name="Weekly diagnostic",
            robot_mission_id="DiagnosticRoutine",
            tasks=[],
        )
    )
    assert mission.id == "execution-id"
    assert mission.name == "Weekly diagnostic"
    assert mission.robot_mission_id == "DiagnosticRoutine"
    assert mission.tasks == []
    assert Mission.model_validate_json(mission.model_dump_json()) == mission


@pytest.mark.parametrize("robot_mission_id", [None, "", " ", "\t\n"])
def test_empty_or_blank_mission_rejected(robot_mission_id: str | None) -> None:
    with pytest.raises(MissionFormatError):
        to_isar_mission(
            StartMissionDefinition(
                id="execution-id", tasks=[], robot_mission_id=robot_mission_id
            )
        )


def test_stored_reference_with_inspection_tasks_rejected() -> None:
    definition = DummyMissionDefinition.dummy_start_mission_definition.model_copy(
        deep=True
    )
    definition.robot_mission_id = "DiagnosticRoutine"
    with pytest.raises(MissionFormatError, match="cannot contain inspection tasks"):
        to_isar_mission(definition)


@pytest.mark.parametrize("robot_mission_id", ["", " ", "\t\n"])
def test_robot_interface_rejects_blank_stored_reference(robot_mission_id: str) -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        Mission(id="id", name="name", robot_mission_id=robot_mission_id)


def test_robot_interface_rejects_mixed_stored_mission() -> None:
    with pytest.raises(ValidationError, match="cannot contain tasks"):
        Mission(
            id="id",
            name="name",
            robot_mission_id="DiagnosticRoutine",
            tasks=DummyMissionDefinition.default_mission.tasks,
        )
