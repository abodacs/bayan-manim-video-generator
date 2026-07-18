from pathlib import Path

import pytest

from scripts.container_smoke import (
    SmokeError,
    allocate_run_directory,
    check_docker,
    current_container_user,
    security_args,
)


def test_allocate_run_directory_preserves_previous_runs(tmp_path: Path) -> None:
    first = allocate_run_directory(tmp_path / "smoke")
    second = allocate_run_directory(tmp_path / "smoke")

    assert first.name == "run"
    assert second.name == "run-001"
    assert first.exists()
    assert second.exists()


def test_security_args_deny_network_and_host_privileges() -> None:
    args = security_args("1000:1000")

    assert "none" in args
    assert "--read-only" in args
    assert "--cap-drop=ALL" in args
    assert "no-new-privileges" in args
    assert "--user" in args
    assert "1000:1000" in args


def test_current_container_user_never_returns_root() -> None:
    uid, gid = current_container_user()

    assert uid != "0"
    assert gid.isdigit()


def test_check_docker_explains_missing_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.container_smoke.shutil.which", lambda _: None)

    with pytest.raises(SmokeError, match="Docker CLI was not found"):
        check_docker()
