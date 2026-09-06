"""End-to-end tests for `bayan generate` through the pipeline spine."""

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bayan.cli import app
from bayan.generator.llm_client import LLMConfigError, LLMResponseFormatError
from bayan.pipeline.models import CodeAttemptEvidence
from bayan.testing import FakeProvider
from tests.conftest import MP4_BYTES, PNG_BYTES

ARABIC_PROMPT = "شرح العامل المشترك الأكبر للأعداد ١٢ و ١٨"
RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{4}Z-[0-9a-f]{8}$")

runner = CliRunner()


def _fake_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (FakeProvider(), FakeProvider(), FakeProvider()),
    )


def _run_generate(monkeypatch: pytest.MonkeyPatch, runs_root: Path, *args: str):
    _fake_providers(monkeypatch)
    return runner.invoke(
        app,
        ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root), *args],
    )


def _only_run_dir(runs_root: Path) -> Path:
    run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    return run_dirs[0]


def test_generate_happy_path_creates_run_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output
    assert "Success!" in result.output

    run_dir = _only_run_dir(runs_root)
    assert RUN_ID_PATTERN.match(run_dir.name)
    for artifact in ("plan.json", "scene.py", "draft.mp4", "preview.png", "records", "run.json"):
        assert (run_dir / artifact).exists(), artifact

    assert (run_dir / "draft.mp4").read_bytes() == MP4_BYTES
    assert (run_dir / "preview.png").read_bytes() == PNG_BYTES

    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed"
    assert summary["prompt"] == ARABIC_PROMPT
    assert summary["profile"] == "msa-western"
    assert summary["model"] == "fake-model-v1"
    assert summary["stages"] == {
        "plan": "completed",
        "profile": "completed",
        "code": "completed",
        "gates": "completed",
        "render": "completed",
        "critic": "completed",
    }
    assert summary["failure"] is None


def test_every_stage_writes_one_ordered_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output

    records_dir = _only_run_dir(runs_root) / "records"
    assert sorted(path.name for path in records_dir.glob("*.json")) == [
        "01-plan.json",
        "02-profile.json",
        "03-code.json",
        "04-gates.json",
        "05-render.json",
        "06-critic.json",
    ]
    for record_path in sorted(records_dir.glob("*.json")):
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["status"] == "completed"
        assert record["created_at"]


def test_failing_plan_stage_stops_later_stages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    class _FailingPlanner:
        def generate_lesson_plan(self, prompt: str, profile: str) -> object:
            raise LLMResponseFormatError("provider returned no usable plan")

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (_FailingPlanner(), FakeProvider(), FakeProvider()),
    )
    runs_root = tmp_path / "runs"
    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert "Generation failed" in result.output
    assert "provider returned no usable plan" in result.output

    run_dir = _only_run_dir(runs_root)
    records = sorted(path.name for path in (run_dir / "records").glob("*.json"))
    assert records == ["01-plan.json"]
    assert not (run_dir / "plan.json").exists()
    assert not (run_dir / "scene.py").exists()
    assert not (run_dir / "draft.mp4").exists()

    summary = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["stages"] == {"plan": "failed"}


def test_missing_api_key_fails_fast_before_any_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.delenv("BAYAN_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _no_credentials() -> tuple[object, object]:
        raise LLMConfigError("Missing LLM API key: set BAYAN_API_KEY.")

    monkeypatch.setattr("bayan.cli._build_providers", _no_credentials)
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert "Configuration Error" in result.output
    assert not runs_root.exists() or list(runs_root.iterdir()) == []


def test_run_id_is_deterministic_format(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root)
    assert result.exit_code == 0, result.output
    assert RUN_ID_PATTERN.match(_only_run_dir(runs_root).name)


def test_unknown_profile_is_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _fake_providers(monkeypatch)
    runs_root = tmp_path / "runs"
    result = runner.invoke(
        app,
        ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root), "--profile", "bogus"],
    )

    assert result.exit_code != 0
    # The error names the accepted profiles, straight from the registry.
    assert "Unknown language profile" in result.output
    for known in ("msa-western", "msa-arabic-indic", "egyptian"):
        assert known in result.output
    assert not runs_root.exists() or list(runs_root.iterdir()) == []


def test_generate_help_shows_usage():
    result = runner.invoke(app, ["generate", "--help"])

    assert result.exit_code == 0
    assert "Free-form Arabic lesson prompt" in result.output
    assert "--profile" in result.output
    assert "--runs-root" in result.output


def test_console_script_is_declared():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert "[project.scripts]" in text
    assert 'bayan = "bayan.cli:app"' in text


def test_arabic_gate_blocks_render_before_any_container_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: list[tuple[str, ...]]
):
    """BDD #70: a Text(...) Arabic scene is rejected before Docker ever runs."""
    banned_scene = (
        "from manim import *\n"
        "from bayan.utils.arabic_helper import ArabicText, rtl_glyphs\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        Text("مرحبا بكم")\n'
    )

    class _UngatedCoder:
        def generate_scene_code(
            self, *, plan: object, system_prompt: str, user_prompt: str
        ) -> CodeAttemptEvidence:
            return CodeAttemptEvidence(
                code=banned_scene,
                raw_response=banned_scene,
                fingerprint="scripted",
                model="scripted-model",
                usage=None,
            )

    class _NeverFixRepairer:
        def repair_scene_code(self, *, code: str, classification: object, plan: object):
            return CodeAttemptEvidence(
                code=code, raw_response=code, fingerprint="never-fix", model="fake", usage=None
            )

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (FakeProvider(), _UngatedCoder(), _NeverFixRepairer()),
    )
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert "arabic" in result.output
    assert fake_render == []
    run_dir = _only_run_dir(runs_root)
    assert (run_dir / "records" / "04-gates.json").exists()
    gates_record = json.loads((run_dir / "records" / "04-gates.json").read_text(encoding="utf-8"))
    assert gates_record["status"] == "failed"
    assert not (run_dir / "draft.mp4").exists()


@pytest.mark.parametrize("profile_name", ["msa-western", "msa-arabic-indic", "egyptian"])
def test_cli_accepts_exactly_the_three_profile_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None, profile_name: str
):
    runs_root = tmp_path / "runs" / profile_name
    result = _run_generate(monkeypatch, runs_root, "--profile", profile_name)

    assert result.exit_code == 0, result.output
    summary = json.loads((_only_run_dir(runs_root) / "run.json").read_text(encoding="utf-8"))
    assert summary["profile"] == profile_name


def test_vlm_flag_records_a_not_implemented_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    runs_root = tmp_path / "runs"
    result = _run_generate(monkeypatch, runs_root, "--vlm")

    assert result.exit_code == 0, result.output
    critic_record = json.loads(
        (_only_run_dir(runs_root) / "records" / "06-critic.json").read_text(encoding="utf-8")
    )
    vlm_checks = [check for check in critic_record["checks"] if check["check"] == "vlm"]
    assert vlm_checks == [
        {
            "check": "vlm",
            "status": "not_implemented",
            "evidence": "The VLM critic is not implemented; it is out of scope for the "
            "MVP per epic #68.",
            "suggestion": "Rely on the deterministic checks plus teacher review.",
        }
    ]


def test_repair_loop_fixes_arabic_scene_within_two_attempts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    """BDD #71 success path: a gate failure is repaired and the run completes."""
    bad_scene = (
        "from manim import *\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        Text("\u0645\u0631\u062d\u0628\u0627")\n'
    )
    from bayan.pipeline.models import CodeAttemptEvidence as Evidence

    class _BadCoder(FakeProvider):
        def generate_scene_code(self, *, plan, system_prompt, user_prompt):
            return Evidence(
                code=bad_scene,
                raw_response=bad_scene,
                fingerprint="bad",
                model="fake",
                usage=None,
            )

    class _FullSceneRepairer(FakeProvider):
        def repair_scene_code(self, *, code, classification, plan):
            return self.generate_scene_code(plan=plan, system_prompt="", user_prompt="")

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (FakeProvider(), _BadCoder(), _FullSceneRepairer()),
    )
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 0, result.output
    summary = json.loads((_only_run_dir(runs_root) / "run.json").read_text(encoding="utf-8"))
    assert summary["stages"]["gates"] == "completed"
    assert summary["repairs_used"] == 1


def test_repair_re_gates_once_through_the_gates_stage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: None
):
    """BDD #71: the gates re-run between attempts, exactly once per fix.

    The repair service must not gate the candidate itself -- the gates
    stage is the single place a repaired scene is re-gated, so one repair
    means one initial gate run plus one re-gate, never a third pass.
    """
    bad_scene = (
        "from manim import *\n"
        "\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        Text("\u0645\u0631\u062d\u0628\u0627")\n'
    )
    from bayan.pipeline.models import CodeAttemptEvidence as Evidence

    class _BadCoder(FakeProvider):
        def generate_scene_code(self, *, plan, system_prompt, user_prompt):
            return Evidence(
                code=bad_scene,
                raw_response=bad_scene,
                fingerprint="bad",
                model="fake",
                usage=None,
            )

    class _FullSceneRepairer(FakeProvider):
        def repair_scene_code(self, *, code, classification, plan):
            return self.generate_scene_code(plan=plan, system_prompt="", user_prompt="")

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (FakeProvider(), _BadCoder(), _FullSceneRepairer()),
    )

    import bayan.pipeline.spine as spine_module

    gated_codes: list[str] = []
    original_run_gates = spine_module.run_gates

    def _counting_run_gates(code, *, profile):
        gated_codes.append(code)
        return original_run_gates(code, profile=profile)

    monkeypatch.setattr(spine_module, "run_gates", _counting_run_gates)
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 0, result.output
    assert len(gated_codes) == 2  # the failing original + one re-gate of the fix
    assert gated_codes[0] == bad_scene.strip()
    assert gated_codes[1] != bad_scene.strip()


def test_repair_exhaustion_writes_record_and_exits_non_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: list[tuple[str, ...]]
):
    class _UngatedCoder:
        def generate_scene_code(self, *, plan, system_prompt, user_prompt):
            bad = (
                "from manim import *\n"
                "class GeneratedScene(Scene):\n"
                "    def construct(self):\n"
                '        Text("\u0627\u0644\u0646\u0627\u062a\u062c")\n'
            )
            return CodeAttemptEvidence(
                code=bad, raw_response=bad, fingerprint="bad", model="fake", usage=None
            )

    class _NeverFixRepairer:
        def repair_scene_code(self, *, plan, code, classification):
            bad = (
                "from manim import *\n"
                "class GeneratedScene(Scene):\n"
                "    def construct(self):\n"
                '        Text("\u0627\u0644\u0646\u0627\u062a\u062c")\n'
            )
            return CodeAttemptEvidence(
                code=bad, raw_response=bad, fingerprint="bad", model="fake", usage=None
            )

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (FakeProvider(), _UngatedCoder(), _NeverFixRepairer()),
    )
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert "Generation failed" in result.output
    record = json.loads(
        (_only_run_dir(runs_root) / "records" / "07-repair.json").read_text(encoding="utf-8")
    )
    assert record["status"] == "exhausted"
    summary = json.loads((_only_run_dir(runs_root) / "run.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert fake_render == []


def test_policy_violation_short_circuits_without_llm_repair(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_render: list[tuple[str, ...]]
):
    policy_scene = (
        "from manim import *\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        eval("1 + 1")\n'
    )

    class _PolicyCoder:
        def generate_scene_code(self, *, plan, system_prompt, user_prompt):
            return CodeAttemptEvidence(
                code=policy_scene,
                raw_response=policy_scene,
                fingerprint="policy",
                model="fake",
                usage=None,
            )

    repair_calls: list[int] = []

    class _CountingRepairer:
        def repair_scene_code(self, **kwargs):
            repair_calls.append(1)
            return CodeAttemptEvidence(
                code=policy_scene,
                raw_response=policy_scene,
                fingerprint="policy",
                model="fake",
                usage=None,
            )

    monkeypatch.setattr(
        "bayan.cli._build_providers",
        lambda: (FakeProvider(), _PolicyCoder(), _CountingRepairer()),
    )
    runs_root = tmp_path / "runs"

    result = runner.invoke(app, ["generate", ARABIC_PROMPT, "--runs-root", str(runs_root)])

    assert result.exit_code == 1
    assert repair_calls == []
    assert (_only_run_dir(runs_root) / "review_packet.md").exists()
    assert fake_render == []
