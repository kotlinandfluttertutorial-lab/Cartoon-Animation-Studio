"""
Stage 3 — Garden Render Tests
Verifies the 4 garden preview PNGs exist, have valid PNG headers, render at
640x360, meet minimum size thresholds, and that a single render completes
within the 60s per-image budget. File-existence checks need no Blender; the
timing test requires Blender.
"""

import os
import struct
import subprocess
import tempfile
import time

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

GARDEN_DIR = os.path.join(_STUDIO, "blender", "assets", "environments", "garden")
PREVIEWS = os.path.join(GARDEN_DIR, "previews")
GARDEN_BLEND = os.path.join(GARDEN_DIR, "garden.blend")

BLENDER_MISSING = not os.path.isfile(BLENDER_EXE)

# name -> minimum size in bytes
EXPECTED = {
    "garden_wide.png": 20_000,
    "garden_main.png": 20_000,
    "garden_close.png": 20_000,
    "garden_with_characters.png": 50_000,
}

_PNG_SIGNATURE = b"\x89PNG"


def _png_dimensions(path):
    with open(path, "rb") as fh:
        fh.read(8)   # PNG signature
        fh.read(8)   # IHDR chunk length + type
        ihdr_data = fh.read(8)
    width, height = struct.unpack(">II", ihdr_data)
    return width, height


# ===========================================================================
# Preview existence + size
# ===========================================================================


class TestPreviewsExist:
    def test_all_previews_exist_with_min_size(self):
        problems = []
        for name, min_size in EXPECTED.items():
            path = os.path.join(PREVIEWS, name)
            if not os.path.isfile(path):
                problems.append(f"{name}: missing")
            elif os.path.getsize(path) < min_size:
                problems.append(
                    f"{name}: too small ({os.path.getsize(path)} bytes < {min_size})"
                )
        assert not problems, "Preview issues:\n" + "\n".join(problems)

    def test_combined_preview_present(self):
        path = os.path.join(PREVIEWS, "garden_with_characters.png")
        assert os.path.isfile(path), "garden_with_characters.png must exist"


# ===========================================================================
# PNG header validity
# ===========================================================================


class TestPngHeaders:
    def test_all_previews_valid_png(self):
        failures = []
        for name in EXPECTED:
            path = os.path.join(PREVIEWS, name)
            if not os.path.isfile(path):
                failures.append(f"{name}: missing")
                continue
            with open(path, "rb") as fh:
                header = fh.read(4)
            if header != _PNG_SIGNATURE:
                failures.append(f"{name}: bad header {header!r}")
        assert not failures, "Invalid/missing PNGs:\n" + "\n".join(failures)


# ===========================================================================
# Resolution
# ===========================================================================


class TestRenderResolution:
    def test_all_previews_640x360(self):
        wrong = []
        for name in EXPECTED:
            path = os.path.join(PREVIEWS, name)
            if not os.path.isfile(path):
                wrong.append(f"{name}: missing")
                continue
            try:
                w, h = _png_dimensions(path)
            except Exception as exc:
                wrong.append(f"{name}: read error ({exc})")
                continue
            if (w, h) != (640, 360):
                wrong.append(f"{name}: {w}x{h} (expected 640x360)")
        assert not wrong, "Resolution mismatches:\n" + "\n".join(wrong)


# ===========================================================================
# Render timing (requires Blender)
# ===========================================================================

_skip_no_blender = pytest.mark.skipif(
    BLENDER_MISSING,
    reason=f"Blender executable not found: {BLENDER_EXE}",
)


@_skip_no_blender
class TestRenderTiming:
    def test_single_render_under_60s(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "garden_main_timing.png")
            inline_script = (
                "import bpy\n"
                f"bpy.ops.wm.open_mainfile(filepath={GARDEN_BLEND!r})\n"
                "scene = bpy.context.scene\n"
                "scene.render.engine = 'BLENDER_WORKBENCH'\n"
                "scene.render.resolution_x = 640\n"
                "scene.render.resolution_y = 360\n"
                "scene.render.image_settings.file_format = 'PNG'\n"
                f"scene.render.filepath = {out_path!r}\n"
                "scene.camera = bpy.data.objects['Garden_Main_Camera']\n"
                "sh = scene.display.shading\n"
                "sh.light = 'STUDIO'\n"
                "sh.color_type = 'MATERIAL'\n"
                "sh.show_shadows = True\n"
                "sh.show_cavity = True\n"
                "bpy.ops.render.render(write_still=True)\n"
                "print('RENDER_DONE')\n"
            )
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(inline_script)
                tmp_script = tmp.name
            try:
                start = time.monotonic()
                result = subprocess.run(
                    [BLENDER_EXE, "--background", "--factory-startup",
                     "--python", tmp_script],
                    capture_output=True, text=True, timeout=180,
                )
                elapsed = time.monotonic() - start
            finally:
                os.unlink(tmp_script)

            combined = result.stdout + result.stderr
            assert "RENDER_DONE" in combined, (
                f"Render did not complete (exit {result.returncode}):\n"
                f"{combined[-1500:]}"
            )
            assert elapsed < 60, f"Render took {elapsed:.1f}s — exceeds 60s budget"
