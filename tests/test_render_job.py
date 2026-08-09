from pathlib import Path

import pytest

from bayan.planner.models import RenderSettings, ScenePlan
from bayan.renderer.executor import RenderJobRunner
from bayan.renderer.models import RenderJob


def test_render_job_dataclass_lifecycle() -> None:
    job = RenderJob(
        job_id="job-123",
        status="requested",
        scene_plan_id="plan-123",
        scene_id="ArabicSanityCheck",
    )
    assert job.status == "requested"
    assert "requested" in ["requested", "running", "succeeded", "failed"]

    data = job.to_dict()
    assert data["job_id"] == "job-123"
    assert data["status"] == "requested"


def test_unknown_template_fails_preflight(tmp_path: Path) -> None:
    plan = ScenePlan(
        learning_objective="اختبار القالب",
        language="ar",
        visual_concept="دائرة متحرّكة",
        selected_template="unknown_template_xyz",
        render_settings=RenderSettings(),
        provider_fingerprint="fake-provider-hash",
    )

    runner = RenderJobRunner()

    with pytest.raises(ValueError, match="Unknown or unapproved template"):
        runner.run_job(plan, output_dir=tmp_path)


def test_unsafe_path_traversal_fails_preflight(tmp_path: Path) -> None:
    plan = ScenePlan(
        learning_objective="اختبار الأمان",
        language="ar",
        visual_concept="دائرة",
        selected_template="../../etc/passwd",
        render_settings=RenderSettings(),
        provider_fingerprint="fake-provider-hash",
    )

    runner = RenderJobRunner()

    with pytest.raises(ValueError):
        runner.run_job(plan, output_dir=tmp_path)
