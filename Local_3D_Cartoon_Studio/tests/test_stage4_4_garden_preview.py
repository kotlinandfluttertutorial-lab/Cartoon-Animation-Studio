"""Build and sample the Stage 4 garden timeline in the portable Blender runtime."""

from pathlib import Path
import subprocess

import pytest


PROJECT = Path(__file__).resolve().parents[1]
BLENDER = PROJECT.parent / "tools" / "blender-4.4.3-windows-x64" / "blender.exe"


@pytest.mark.skipif(not BLENDER.is_file(), reason="Portable Blender is unavailable")
def test_garden_animation_timeline(tmp_path):
    result = subprocess.run(
        [
            str(BLENDER), "--background",
            str(PROJECT / "blender/assets/environments/garden/garden.blend"),
            "--python-exit-code", "1", "--python",
            str(PROJECT / "blender/scripts/render_stage44_preview.py"),
            "--", str(tmp_path), "--validate-only",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "STAGE44_TIMELINE_OK" in result.stdout
    assert list(tmp_path.iterdir()) == []
