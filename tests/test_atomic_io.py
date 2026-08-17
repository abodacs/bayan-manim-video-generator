from pathlib import Path

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
