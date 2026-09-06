from pathlib import Path

import pytest

from bayan.utils.atomic_io import atomic_write_text


def test_atomic_write_text_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"

    atomic_write_text(target, '{"status": "ok"}\n')

    assert target.read_text(encoding="utf-8") == '{"status": "ok"}\n'
    assert not (tmp_path / "manifest.json.tmp").exists()


def test_atomic_write_text_replaces_existing_content(tmp_path: Path) -> None:
    target = tmp_path / "scene_plan.json"
    atomic_write_text(target, "old")

    atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "new"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_text_cleans_up_the_temp_file_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "manifest.json"
    atomic_write_text(target, "old")

    def failing_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise OSError("replace failed")

    monkeypatch.setattr("bayan.utils.atomic_io.os.replace", failing_replace)

    with pytest.raises(OSError, match="replace failed"):
        atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.iterdir()) == [target]
