from pathlib import Path

import pytest

from bayan.planner.models import PlanRenderPreferences, ScenePlan
from bayan.renderer.executor import RenderJobRunner
from bayan.renderer.models import RenderJob
from bayan.templates.catalogue import get_template_catalogue


def test_render_job_dataclass_lifecycle() -> None:
    job = RenderJob(
        job_id="job-123",
        status="requested",
        scene_plan_id="plan-123",
        scene_id="ArabicSanityCheck",
    )
    assert job.status == "requested"

    data = job.to_dict()
    assert data["job_id"] == "job-123"
    assert data["status"] == "requested"


def _plan_for(template: str) -> ScenePlan:
    return ScenePlan(
        learning_objective="اختبار القالب",
        language="ar",
        visual_concept="دائرة متحرّكة",
        selected_template=template,
        render_settings=PlanRenderPreferences(),
        provider_fingerprint="fake-provider-hash",
    )


@pytest.mark.parametrize("slug", sorted(get_template_catalogue().keys()))
def test_every_catalogue_template_passes_preflight(slug: str, tmp_path: Path) -> None:
    runner = RenderJobRunner()

    job = runner.run_job(_plan_for(slug), output_dir=tmp_path)

    assert job.status == "requested"
    assert job.scene_id == slug


@pytest.mark.parametrize(
    "template",
    [
        "arabic_template",
        "ArabicSanityCheck",
        "إنشاء دائرة",
        "unknown_template_xyz",
        "../../etc/passwd",
    ],
)
def test_non_catalogue_template_fails_preflight(template: str, tmp_path: Path) -> None:
    runner = RenderJobRunner()

    with pytest.raises(ValueError, match="Unknown or unapproved template"):
        runner.run_job(_plan_for(template), output_dir=tmp_path)
