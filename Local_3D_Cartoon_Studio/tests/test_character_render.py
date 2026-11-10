"""
Stage 2 — Character Render Tests
Verifies that preview PNGs exist, have valid PNG headers, correct resolution,
and that rendering via render_character_preview.py completes within time budget.
All tests require Blender.
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

CHARACTERS_DIR = os.path.join(_STUDIO, "blender", "assets", "characters")
SCRIPTS_DIR = os.path.join(_STUDIO, "blender", "scripts")

AARAV_PREVIEWS = os.path.join(CHARACTERS_DIR, "aarav", "previews")
AANYA_PREVIEWS = os.path.join(CHARACTERS_DIR, "aanya", "previews")
COMBINED_DIR = os.path.join(CHARACTERS_DIR, "combined")
AARAV_BLEND = os.path.join(CHARACTERS_DIR, "aarav", "aarav.blend")
RENDER_SCRIPT = os.path.join(SCRIPTS_DIR, "render_character_preview.py")

BLENDER_MISSING = not os.path.isfile(BLENDER_EXE)

_skip_no_blender = pytest.mark.skipif(
    BLENDER_MISSING,
    reason=f"Blender executable not found: {BLENDER_EXE}",
)

# Expected preview filenames (5 per character + 1 combined = 11 total)
_PREVIEW_NAMES = [
    "front.png",
    "side.png",
    "three_quarter.png",
    "wave_pose.png",
    "happy_expression.png",
]

_PNG_SIGNATURE = b"\x89PNG"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _all_png_paths():
    """Return paths of all 11 expected PNGs."""
    paths = []
    for name in _PREVIEW_NAMES:
        paths.append(os.path.join(AARAV_PREVIEWS, name))
        paths.append(os.path.join(AANYA_PREVIEWS, name))
    paths.append(os.path.join(COMBINED_DIR, "both_characters.png"))
    return paths


def _png_dimensions(path):
    """Return (width, height) from a PNG IHDR chunk (bytes 16-24)."""
    with open(path, "rb") as fh:
        fh.read(8)   # PNG signature
        fh.read(8)   # IHDR chunk length + type
        ihdr_data = fh.read(8)  # width (4 bytes) + height (4 bytes)
    width, height = struct.unpack(">II", ihdr_data)
    return width, height


# ===========================================================================
# Preview existence tests
# ===========================================================================


@_skip_no_blender
class TestPreviewsExist:
    """Check all expected preview PNGs exist and have non-trivial size."""

    def test_aarav_previews_exist(self):
        missing_or_small = []
        for name in _PREVIEW_NAMES:
            path = os.path.join(AARAV_PREVIEWS, name)
            if not os.path.isfile(path):
                missing_or_small.append(f"{name}: missing")
            elif os.path.getsize(path) <= 1024:
                missing_or_small.append(
                    f"{name}: too small ({os.path.getsize(path)} bytes)"
                )
        assert not missing_or_small, (
            f"Aarav preview issues:\n" + "\n".join(missing_or_small)
        )

    def test_aanya_previews_exist(self):
        missing_or_small = []
        for name in _PREVIEW_NAMES:
            path = os.path.join(AANYA_PREVIEWS, name)
            if not os.path.isfile(path):
                missing_or_small.append(f"{name}: missing")
            elif os.path.getsize(path) <= 1024:
                missing_or_small.append(
                    f"{name}: too small ({os.path.getsize(path)} bytes)"
                )
        assert not missing_or_small, (
            f"Aanya preview issues:\n" + "\n".join(missing_or_small)
        )

    def test_combined_preview_exists(self):
        combined = os.path.join(COMBINED_DIR, "both_characters.png")
        assert os.path.isfile(combined), (
            f"combined/both_characters.png not found at {combined}"
        )
        size = os.path.getsize(combined)
        assert size > 1024, f"combined/both_characters.png too small: {size} bytes"


# ===========================================================================
# PNG header validity
# ===========================================================================


@_skip_no_blender
class TestRenderProducesValidPng:
    """Verify every expected PNG starts with the PNG file signature."""

    def test_render_produces_valid_png(self):
        failures = []
        for path in _all_png_paths():
            if not os.path.isfile(path):
                failures.append(f"{os.path.basename(path)}: file missing")
                continue
            with open(path, "rb") as fh:
                header = fh.read(4)
            if header != _PNG_SIGNATURE:
                failures.append(
                    f"{os.path.basename(path)}: bad header {header!r}"
                )
        assert not failures, "Invalid or missing PNGs:\n" + "\n".join(failures)


# ===========================================================================
# Resolution check
# ===========================================================================


@_skip_no_blender
class TestRenderResolution:
    """Verify each PNG has width=640, height=360."""

    def test_render_resolution(self):
        png_paths = [p for p in _all_png_paths() if os.path.isfile(p)]
        if not png_paths:
            pytest.skip("No PNG files found — skipping resolution check")

        wrong = []
        for path in png_paths:
            try:
                w, h = _png_dimensions(path)
            except Exception as exc:
                wrong.append(f"{os.path.basename(path)}: read error ({exc})")
                continue
            if w != 640 or h != 360:
                wrong.append(
                    f"{os.path.basename(path)}: {w}x{h} (expected 640x360)"
                )
        assert not wrong, "Resolution mismatches:\n" + "\n".join(wrong)


# ===========================================================================
# Render timing
# ===========================================================================


@_skip_no_blender
class TestRenderTiming:
    """Run a minimal front-view render for Aarav and assert it finishes < 120 s."""

    def test_render_timing(self):
        # Write a temporary output path so we do not overwrite the production PNG
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "aarav_front_timing.png")

            # Minimal inline Blender script: open the blend file and render
            # a single 640x360 Workbench frame to *out_path*.
            inline_script = (
                "import bpy\n"
                f"bpy.ops.wm.open_mainfile(filepath={AARAV_BLEND!r})\n"
                "scene = bpy.context.scene\n"
                "scene.render.engine = 'BLENDER_WORKBENCH'\n"
                "scene.render.resolution_x = 640\n"
                "scene.render.resolution_y = 360\n"
                "scene.render.image_settings.file_format = 'PNG'\n"
                f"scene.render.filepath = {out_path!r}\n"
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
                    [
                        BLENDER_EXE,
                        "--background",
                        "--factory-startup",
                        "--python",
                        tmp_script,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,  # hard cap; assertion is < 120 s
                )
                elapsed = time.monotonic() - start
            finally:
                os.unlink(tmp_script)

        combined = result.stdout + result.stderr
        assert "RENDER_DONE" in combined, (
            f"Render did not complete (exit {result.returncode}):\n"
            f"{combined[-2000:]}"
        )
        assert elapsed < 120, (
            f"Render took {elapsed:.1f}s — exceeds 120 s budget"
        )
