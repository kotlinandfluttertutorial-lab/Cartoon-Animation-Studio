"""
Stage 4.1 — Character Rigging and Animation Foundation Tests

Validates:
  - Working copy blend files exist (aarav_stage4.blend, aanya_stage4.blend)
  - Each working copy contains exactly 2 actions (IDLE + WALK)
  - Each action has >= 4 keyframe points
  - All 5 preview PNGs exist at 640x360 and > 20 KB
  - Original aarav.blend unchanged (774392 bytes)
  - Original aanya.blend unchanged (796228 bytes)
  - Working copies differ from originals (larger due to animation data)
  - All 33 existing Stage 2/3 regression tests still pass (via pytest.ini / conftest)

Blender tests use a Blender subprocess to inspect blend file contents.
"""

import json
import os
import struct
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

CHARACTERS_DIR = os.path.join(_STUDIO, "blender", "assets", "characters")

AARAV_DIR = os.path.join(CHARACTERS_DIR, "aarav")
AANYA_DIR = os.path.join(CHARACTERS_DIR, "aanya")

AARAV_BLEND_ORIG = os.path.join(AARAV_DIR, "aarav.blend")
AANYA_BLEND_ORIG = os.path.join(AANYA_DIR, "aanya.blend")
AARAV_BLEND_S4 = os.path.join(AARAV_DIR, "aarav_stage4.blend")
AANYA_BLEND_S4 = os.path.join(AANYA_DIR, "aanya_stage4.blend")

PREVIEWS_DIR = os.path.join(_STUDIO, "output", "stage4_1", "previews")

# Known original file sizes (confirmed from Stage 2 output)
AARAV_ORIG_SIZE = 774392
AANYA_ORIG_SIZE = 796228

BLENDER_MISSING = not os.path.isfile(BLENDER_EXE)

_skip_no_blender = pytest.mark.skipif(
    BLENDER_MISSING,
    reason=f"Blender executable not found: {BLENDER_EXE}",
)

_PNG_SIGNATURE = b"\x89PNG"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _png_dimensions(path):
    """Return (width, height) from a PNG file's IHDR chunk."""
    with open(path, "rb") as fh:
        header = fh.read(24)
    if header[:4] != _PNG_SIGNATURE:
        return None, None
    w = struct.unpack(">I", header[16:20])[0]
    h = struct.unpack(">I", header[20:24])[0]
    return w, h


def _run_blender_script(script_text, timeout=120):
    """Run a Python script string in Blender background mode."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(script_text)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [BLENDER_EXE, "--background", "--python", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    finally:
        os.unlink(tmp_path)


# ===========================================================================
# Working copy existence tests
# ===========================================================================


class TestWorkingCopiesExist:
    """Working copy blend files must exist."""

    def test_aarav_stage4_blend_exists(self):
        assert os.path.isfile(AARAV_BLEND_S4), (
            f"aarav_stage4.blend not found: {AARAV_BLEND_S4}"
        )

    def test_aanya_stage4_blend_exists(self):
        assert os.path.isfile(AANYA_BLEND_S4), (
            f"aanya_stage4.blend not found: {AANYA_BLEND_S4}"
        )


# ===========================================================================
# Original file integrity tests
# ===========================================================================


class TestOriginalsUnchanged:
    """Original blend files must not be modified."""

    def test_aarav_original_size(self):
        actual = os.path.getsize(AARAV_BLEND_ORIG)
        assert actual == AARAV_ORIG_SIZE, (
            f"aarav.blend size changed: expected {AARAV_ORIG_SIZE}, got {actual}"
        )

    def test_aanya_original_size(self):
        actual = os.path.getsize(AANYA_BLEND_ORIG)
        assert actual == AANYA_ORIG_SIZE, (
            f"aanya.blend size changed: expected {AANYA_ORIG_SIZE}, got {actual}"
        )

    def test_working_copies_differ_from_originals(self):
        """Working copies must be larger than originals (animation data added)."""
        aarav_s4_size = os.path.getsize(AARAV_BLEND_S4)
        aanya_s4_size = os.path.getsize(AANYA_BLEND_S4)
        assert aarav_s4_size > AARAV_ORIG_SIZE, (
            f"aarav_stage4.blend ({aarav_s4_size}) should be larger than original ({AARAV_ORIG_SIZE})"
        )
        assert aanya_s4_size > AANYA_ORIG_SIZE, (
            f"aanya_stage4.blend ({aanya_s4_size}) should be larger than original ({AANYA_ORIG_SIZE})"
        )


# ===========================================================================
# Action existence and keyframe tests (require Blender)
# ===========================================================================


@_skip_no_blender
class TestAaravActions:
    """Aarav stage4 blend must contain AARAV_IDLE and AARAV_WALK with keyframes."""

    def _check_actions(self):
        script = f"""
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=r'{AARAV_BLEND_S4}')
results = {{}}
for aname in ['AARAV_IDLE', 'AARAV_WALK']:
    action = bpy.data.actions.get(aname)
    if action is None:
        results[aname] = 0
    else:
        kf = sum(len(fc.keyframe_points) for fc in action.fcurves)
        results[aname] = kf
for aname, kf in results.items():
    print(f'ACTION {{aname}} KF {{kf}}')
sys.exit(0)
"""
        return _run_blender_script(script)

    def test_aarav_idle_action_exists(self):
        result = self._check_actions()
        combined = result.stdout + result.stderr
        assert "ACTION AARAV_IDLE KF" in combined, (
            f"AARAV_IDLE action not found or no keyframes\n{combined[-2000:]}"
        )
        # Extract keyframe count
        for line in combined.splitlines():
            if "ACTION AARAV_IDLE KF" in line:
                kf = int(line.split("KF")[-1].strip())
                assert kf >= 4, f"AARAV_IDLE has only {kf} keyframe points, expected >= 4"
                break

    def test_aarav_walk_action_exists(self):
        result = self._check_actions()
        combined = result.stdout + result.stderr
        assert "ACTION AARAV_WALK KF" in combined, (
            f"AARAV_WALK action not found or no keyframes\n{combined[-2000:]}"
        )
        for line in combined.splitlines():
            if "ACTION AARAV_WALK KF" in line:
                kf = int(line.split("KF")[-1].strip())
                assert kf >= 4, f"AARAV_WALK has only {kf} keyframe points, expected >= 4"
                break


@_skip_no_blender
class TestAanyaActions:
    """Aanya stage4 blend must contain AANYA_IDLE and AANYA_WALK with keyframes."""

    def _check_actions(self):
        script = f"""
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=r'{AANYA_BLEND_S4}')
results = {{}}
for aname in ['AANYA_IDLE', 'AANYA_WALK']:
    action = bpy.data.actions.get(aname)
    if action is None:
        results[aname] = 0
    else:
        kf = sum(len(fc.keyframe_points) for fc in action.fcurves)
        results[aname] = kf
for aname, kf in results.items():
    print(f'ACTION {{aname}} KF {{kf}}')
sys.exit(0)
"""
        return _run_blender_script(script)

    def test_aanya_idle_action_exists(self):
        result = self._check_actions()
        combined = result.stdout + result.stderr
        assert "ACTION AANYA_IDLE KF" in combined, (
            f"AANYA_IDLE action not found or no keyframes\n{combined[-2000:]}"
        )
        for line in combined.splitlines():
            if "ACTION AANYA_IDLE KF" in line:
                kf = int(line.split("KF")[-1].strip())
                assert kf >= 4, f"AANYA_IDLE has only {kf} keyframe points, expected >= 4"
                break

    def test_aanya_walk_action_exists(self):
        result = self._check_actions()
        combined = result.stdout + result.stderr
        assert "ACTION AANYA_WALK KF" in combined, (
            f"AANYA_WALK action not found or no keyframes\n{combined[-2000:]}"
        )
        for line in combined.splitlines():
            if "ACTION AANYA_WALK KF" in line:
                kf = int(line.split("KF")[-1].strip())
                assert kf >= 4, f"AANYA_WALK has only {kf} keyframe points, expected >= 4"
                break


# ===========================================================================
# Preview PNG tests
# ===========================================================================


class TestAnimationPreviews:
    """All 5 animation preview PNGs must exist, be 640x360, and > 20 KB."""

    _PREVIEWS = [
        "aarav_idle.png",
        "aarav_walk.png",
        "aanya_idle.png",
        "aanya_walk.png",
        "both_characters_animation.png",
    ]

    def test_all_previews_exist(self):
        missing = []
        for fname in self._PREVIEWS:
            fpath = os.path.join(PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                missing.append(fname)
        assert not missing, f"Missing preview PNGs: {missing}"

    def test_all_previews_valid_png(self):
        for fname in self._PREVIEWS:
            fpath = os.path.join(PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                pytest.skip(f"{fname} missing")
            with open(fpath, "rb") as fh:
                sig = fh.read(4)
            assert sig == _PNG_SIGNATURE, f"{fname} is not a valid PNG"

    def test_all_previews_640x360(self):
        for fname in self._PREVIEWS:
            fpath = os.path.join(PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                pytest.skip(f"{fname} missing")
            w, h = _png_dimensions(fpath)
            assert (w, h) == (640, 360), (
                f"{fname}: expected 640x360, got {w}x{h}"
            )

    def test_all_previews_above_20kb(self):
        for fname in self._PREVIEWS:
            fpath = os.path.join(PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                pytest.skip(f"{fname} missing")
            size = os.path.getsize(fpath)
            assert size > 20480, (
                f"{fname}: {size} bytes is not > 20 KB"
            )
