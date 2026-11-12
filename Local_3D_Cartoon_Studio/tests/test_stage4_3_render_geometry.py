"""Regression checks against the actual Stage 4 Blender meshes and render helpers."""

from hashlib import sha256
from pathlib import Path
import subprocess

import pytest


PROJECT = Path(__file__).resolve().parents[1]
BLENDER = PROJECT.parent / "tools" / "blender-4.4.3-windows-x64" / "blender.exe"
SCRIPTS = PROJECT / "blender" / "scripts"
PROBE = Path(__file__).with_name("blender_stage43_probe.py")


@pytest.mark.skipif(not BLENDER.is_file(), reason="Portable Blender is unavailable")
@pytest.mark.parametrize("character", ["Aarav", "Aanya"])
def test_facial_preview_geometry_and_restore(character):
    name = character.lower()
    directory = PROJECT / "blender" / "assets" / "characters" / name
    original = directory / f"{name}.blend"
    working = directory / f"{name}_stage4.blend"
    before = [sha256(path.read_bytes()).digest() for path in (original, working)]

    result = subprocess.run(
        [
            str(BLENDER), "--background", str(working), "--python-exit-code", "1",
            "--python", str(PROBE), "--", str(SCRIPTS), character,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "FACIAL_PREVIEW_GEOMETRY_OK" in result.stdout
    assert [sha256(path.read_bytes()).digest() for path in (original, working)] == before
