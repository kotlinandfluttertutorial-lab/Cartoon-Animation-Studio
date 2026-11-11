"""
Stage 3 — Garden Generation Tests
Verifies the garden .blend, garden.json, collection list, generation timing,
and idempotency (re-running create_garden.py does not duplicate objects).
"""

import json
import os
import subprocess
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

SCRIPTS_DIR = os.path.join(_STUDIO, "blender", "scripts")
GARDEN_DIR = os.path.join(_STUDIO, "blender", "assets", "environments", "garden")
GARDEN_BLEND = os.path.join(GARDEN_DIR, "garden.blend")
GARDEN_JSON = os.path.join(GARDEN_DIR, "garden.json")
CREATE_GARDEN_PY = os.path.join(SCRIPTS_DIR, "create_garden.py")

BLENDER_MISSING = not os.path.isfile(BLENDER_EXE)

COLLECTIONS = [
    "Environment_Ground", "Environment_Path", "Environment_Trees",
    "Environment_Bushes", "Environment_Flowers", "Environment_Decorations",
    "Environment_Sky", "Lighting", "Cameras",
]


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ===========================================================================
# Unit tests (no Blender required) — verify files already generated
# ===========================================================================


class TestGardenBlendFile:
    def test_blend_exists_and_large(self):
        assert os.path.isfile(GARDEN_BLEND), f"garden.blend not found at {GARDEN_BLEND}"
        size = os.path.getsize(GARDEN_BLEND)
        assert size > 100_000, f"garden.blend too small: {size} bytes"


class TestGardenJson:
    def test_json_exists_and_valid_structure(self):
        assert os.path.isfile(GARDEN_JSON), f"garden.json not found at {GARDEN_JSON}"
        data = _load_json(GARDEN_JSON)
        assert data["environment_id"] == "garden"
        assert "statistics" in data
        assert "collections" in data
        assert "cameras" in data
        assert "previews" in data

    def test_real_polygon_count(self):
        data = _load_json(GARDEN_JSON)
        assert data["statistics"]["total_polygons"] > 0, "total_polygons must be > 0"

    def test_generation_time_recorded(self):
        data = _load_json(GARDEN_JSON)
        assert data["statistics"]["generation_time_s"] > 0, "generation_time_s must be > 0"

    def test_all_9_collections_listed(self):
        data = _load_json(GARDEN_JSON)
        missing = [c for c in COLLECTIONS if c not in data["collections"]]
        assert not missing, f"Missing collections in garden.json: {missing}"


# ===========================================================================
# Integration tests (require Blender)
# ===========================================================================

_skip_no_blender = pytest.mark.skipif(
    BLENDER_MISSING,
    reason=f"Blender executable not found: {BLENDER_EXE}",
)


@_skip_no_blender
class TestGenerationIdempotency:
    def test_rerun_does_not_duplicate_objects(self):
        # Re-run create_garden.py twice; each rebuilds from a clean scene.
        for _ in range(2):
            result = subprocess.run(
                [BLENDER_EXE, "--background", "--factory-startup",
                 "--python", CREATE_GARDEN_PY],
                capture_output=True, text=True, timeout=300,
            )
            assert result.returncode == 0, (
                f"create_garden.py exited {result.returncode}\n"
                f"stdout: {result.stdout[-1500:]}\n"
                f"stderr: {result.stderr[-1500:]}"
            )

        # Open the blend and confirm Ground_Plane is unique (no duplication).
        inline_script = (
            "import bpy\n"
            f"bpy.ops.wm.open_mainfile(filepath={GARDEN_BLEND!r})\n"
            "gp = sum(1 for o in bpy.data.objects if o.name == 'Ground_Plane')\n"
            "trees = sum(1 for o in bpy.data.objects if o.name.startswith('Tree_') and o.name.endswith('_Trunk'))\n"
            "n = len(bpy.data.objects)\n"
            "print(f'GP={gp} TREES={trees} N={n}')\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(inline_script)
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                [BLENDER_EXE, "--background", "--factory-startup",
                 "--python", tmp_path],
                capture_output=True, text=True, timeout=120,
            )
            combined = result.stdout + result.stderr
            assert "GP=1" in combined, (
                f"Ground_Plane not unique after re-run:\n{combined[-1500:]}"
            )
            assert "TREES=5" in combined, (
                f"Expected 5 trees after re-run:\n{combined[-1500:]}"
            )
        finally:
            os.unlink(tmp_path)
