"""RunContext split tests: frozen inputs, append-only typed artifacts."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from bayan.pipeline.models import LessonBeat, LessonPlan
from bayan.pipeline.spine import RunArtifacts, RunInputs, StagePreconditionError


def _plan() -> LessonPlan:
    return LessonPlan(
        topic="divisibility",
        beats=[
            LessonBeat(title="step", on_screen_text="نقسم", insight_move="reveal", numbers=[12])
        ],
    )


def test_inputs_are_frozen():
    inputs = RunInputs(
        run_dir=Path("runs/x"), prompt="prompt", profile="msa-western", quality="draft"
    )

    with pytest.raises(FrozenInstanceError):
        inputs.prompt = "another prompt"  # type: ignore[misc]


def test_require_plan_names_the_missing_stage():
    with pytest.raises(StagePreconditionError, match="plan stage never ran"):
        RunArtifacts().require_plan()


def test_require_scene_code_names_the_missing_stage():
    with pytest.raises(StagePreconditionError, match="code stage never ran"):
        RunArtifacts().require_scene_code()


def test_artifact_readers_succeed_once_their_stage_wrote():
    artifacts = RunArtifacts()
    artifacts.put_plan(_plan())
    artifacts.put_scene_code("class GeneratedScene(Scene):\n    pass\n")

    assert artifacts.require_plan().topic == "divisibility"
    assert artifacts.require_scene_code().startswith("class GeneratedScene")
