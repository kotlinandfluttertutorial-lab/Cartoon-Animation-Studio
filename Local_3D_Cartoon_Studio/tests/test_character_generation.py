"""
Stage 2 — Character Generation Tests
Tests for Aarav and Aanya character generation scripts and assets.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDIO = os.path.dirname(_HERE)

BLENDER_EXE = os.path.join(
    _STUDIO, os.pardir, "tools", "blender-4.4.3-windows-x64", "blender.exe"
)
BLENDER_EXE = os.path.normpath(BLENDER_EXE)

CHARACTERS_DIR = os.path.join(_STUDIO, "blender", "assets", "characters")
SCRIPTS_DIR = os.path.join(_STUDIO, "blender", "scripts")

AARAV_DIR = os.path.join(CHARACTERS_DIR, "aarav")
AANYA_DIR = os.path.join(CHARACTERS_DIR, "aanya")
AARAV_BLEND = os.path.join(AARAV_DIR, "aarav.blend")
AANYA_BLEND = os.path.join(AANYA_DIR, "aanya.blend")
AARAV_JSON = os.path.join(AARAV_DIR, "character.json")
AANYA_JSON = os.path.join(AANYA_DIR, "character.json")

CREATE_AARAV_PY = os.path.join(SCRIPTS_DIR, "create_aarav.py")

BLENDER_MISSING = not os.path.isfile(BLENDER_EXE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_REQUIRED_KEYS = {
    "character_id",
    "character_name",
    "statistics",
    "expressions",
    "poses",
    "previews",
    "materials",
    "bones",
}


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ===========================================================================
# Unit tests (no Blender required)
# ===========================================================================


class TestCharacterJsonSchema:
    """Verify character.json structure for both characters."""

    @pytest.mark.parametrize(
        "json_path,char_name",
        [
            (AARAV_JSON, "aarav"),
            (AANYA_JSON, "aanya"),
        ],
    )
    def test_character_json_schema(self, json_path, char_name):
        assert os.path.isfile(json_path), f"character.json not found for {char_name}"
        data = _load_json(json_path)

        missing = _REQUIRED_KEYS - set(data.keys())
        assert not missing, f"{char_name}: missing keys: {missing}"

        assert data["statistics"]["total_polygons"] > 0, (
            f"{char_name}: total_polygons must be > 0"
        )

        assert len(data["expressions"]) == 4, (
            f"{char_name}: expected 4 expressions, got {len(data['expressions'])}"
        )

        assert len(data["poses"]) == 3, (
            f"{char_name}: expected 3 poses, got {len(data['poses'])}"
        )


class TestCharacterJsonPreviewPaths:
    """Verify that all 5 expected preview keys exist in character.json."""

    _EXPECTED_PREVIEW_KEYS = {
        "front",
        "side",
        "three_quarter",
        "wave_pose",
        "happy_expression",
    }

    @pytest.mark.parametrize(
        "json_path,char_name",
        [
            (AARAV_JSON, "aarav"),
            (AANYA_JSON, "aanya"),
        ],
    )
    def test_character_json_preview_paths(self, json_path, char_name):
        assert os.path.isfile(json_path), f"character.json not found for {char_name}"
        data = _load_json(json_path)

        previews = data.get("previews", {})
        missing = self._EXPECTED_PREVIEW_KEYS - set(previews.keys())
        assert not missing, (
            f"{char_name}: missing preview keys: {missing}"
        )

        assert len(previews) == 5, (
            f"{char_name}: expected exactly 5 preview entries, got {len(previews)}"
        )


class TestScriptFilesExist:
    """Verify required generation scripts are present."""

    _EXPECTED_SCRIPTS = [
        "create_aarav.py",
        "create_aanya.py",
        "character_utils.py",
        "validate_character.py",
        "render_character_preview.py",
    ]

    def test_script_files_exist(self):
        missing = []
        for script in self._EXPECTED_SCRIPTS:
            path = os.path.join(SCRIPTS_DIR, script)
            if not os.path.isfile(path):
                missing.append(script)
        assert not missing, f"Missing scripts in {SCRIPTS_DIR}: {missing}"


# ===========================================================================
# Integration tests (require Blender)
# ===========================================================================

_skip_no_blender = pytest.mark.skipif(
    BLENDER_MISSING,
    reason=f"Blender executable not found: {BLENDER_EXE}",
)


@_skip_no_blender
class TestBlendFilesExist:
    """Verify .blend files are present and have a meaningful size."""

    def test_aarav_blend_exists(self):
        assert os.path.isfile(AARAV_BLEND), f"aarav.blend not found at {AARAV_BLEND}"
        size = os.path.getsize(AARAV_BLEND)
        assert size > 50_000, f"aarav.blend too small: {size} bytes"

    def test_aanya_blend_exists(self):
        assert os.path.isfile(AANYA_BLEND), f"aanya.blend not found at {AANYA_BLEND}"
        size = os.path.getsize(AANYA_BLEND)
        assert size > 50_000, f"aanya.blend too small: {size} bytes"


@_skip_no_blender
class TestGenerationIdempotency:
    """Re-run create_aarav.py and verify no corruption and backup creation."""

    def test_generation_idempotency(self):
        result = subprocess.run(
            [
                BLENDER_EXE,
                "--background",
                "--factory-startup",
                "--python",
                CREATE_AARAV_PY,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"create_aarav.py exited with code {result.returncode}\n"
            f"stdout: {result.stdout[-2000:]}\n"
            f"stderr: {result.stderr[-2000:]}"
        )

        # A versioned backup should exist in the aarav directory
        import glob as _glob

        backups = _glob.glob(os.path.join(AARAV_DIR, "aarav_v*.blend"))
        assert backups, (
            f"No versioned backup (aarav_v*.blend) found in {AARAV_DIR} after re-run"
        )

    def test_no_duplicate_objects(self):
        """After a re-run, aarav.blend must contain exactly one Aarav_Head object."""
        inline_script = (
            "import bpy\n"
            f"bpy.ops.wm.open_mainfile(filepath={AARAV_BLEND!r})\n"
            "count = sum(1 for obj in bpy.data.objects if obj.name == 'Aarav_Head')\n"
            "print('PASS' if count == 1 else f'FAIL count={count}')\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(inline_script)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [
                    BLENDER_EXE,
                    "--background",
                    "--factory-startup",
                    "--python",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            combined = result.stdout + result.stderr
            assert "PASS" in combined, (
                f"Expected 'PASS' in Blender output, got:\n{combined[-2000:]}"
            )
        finally:
            os.unlink(tmp_path)
