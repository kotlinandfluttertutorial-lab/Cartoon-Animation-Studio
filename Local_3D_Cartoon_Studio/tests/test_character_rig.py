"""
Stage 2 — Character Rig Tests
Validates armature bones, validation reports, and pose application for
Aarav and Aanya. All tests require Blender.
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

CHARACTERS_DIR = os.path.join(_STUDIO, "blender", "assets", "characters")
SCRIPTS_DIR = os.path.join(_STUDIO, "blender", "scripts")

AARAV_DIR = os.path.join(CHARACTERS_DIR, "aarav")
AANYA_DIR = os.path.join(CHARACTERS_DIR, "aanya")
AARAV_BLEND = os.path.join(AARAV_DIR, "aarav.blend")
AANYA_BLEND = os.path.join(AANYA_DIR, "aanya.blend")
AARAV_CHAR_JSON = os.path.join(AARAV_DIR, "character.json")
AANYA_CHAR_JSON = os.path.join(AANYA_DIR, "character.json")
AARAV_VAL_JSON = os.path.join(AARAV_DIR, "validation.json")
AANYA_VAL_JSON = os.path.join(AANYA_DIR, "validation.json")
VALIDATE_SCRIPT = os.path.join(SCRIPTS_DIR, "validate_character.py")

BLENDER_MISSING = not os.path.isfile(BLENDER_EXE)

_skip_no_blender = pytest.mark.skipif(
    BLENDER_MISSING,
    reason=f"Blender executable not found: {BLENDER_EXE}",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _run_blender(script_path, timeout=120):
    """Run a Python script in Blender background mode and return CompletedProcess."""
    return subprocess.run(
        [
            BLENDER_EXE,
            "--background",
            "--factory-startup",
            "--python",
            script_path,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_validate(blend_path):
    """Execute validate_character.py against *blend_path* via Blender."""
    result = subprocess.run(
        [
            BLENDER_EXE,
            "--background",
            "--factory-startup",
            "--python",
            VALIDATE_SCRIPT,
            "--",
            blend_path,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result


# ===========================================================================
# Validation report tests
# ===========================================================================


@_skip_no_blender
class TestValidationPass:
    """Run validate_character.py and confirm overall==PASS."""

    def test_aarav_validation_pass(self):
        result = _run_validate(AARAV_BLEND)
        assert result.returncode == 0, (
            f"validate_character.py failed for aarav (exit {result.returncode})\n"
            f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
        )
        assert os.path.isfile(AARAV_VAL_JSON), (
            f"validation.json not written for aarav at {AARAV_VAL_JSON}"
        )
        data = _load_json(AARAV_VAL_JSON)
        assert data.get("overall") == "PASS", (
            f"Aarav validation overall is {data.get('overall')!r}, expected 'PASS'"
        )

    def test_aanya_validation_pass(self):
        result = _run_validate(AANYA_BLEND)
        assert result.returncode == 0, (
            f"validate_character.py failed for aanya (exit {result.returncode})\n"
            f"stdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
        )
        assert os.path.isfile(AANYA_VAL_JSON), (
            f"validation.json not written for aanya at {AANYA_VAL_JSON}"
        )
        data = _load_json(AANYA_VAL_JSON)
        assert data.get("overall") == "PASS", (
            f"Aanya validation overall is {data.get('overall')!r}, expected 'PASS'"
        )


# ===========================================================================
# Bone presence tests (read from validation.json — no Blender subprocess needed
# for these two, but keep the skipif so they are consistent with the suite)
# ===========================================================================


@_skip_no_blender
class TestAllBones:
    """Verify validation.json reports no missing bones."""

    def test_aarav_all_bones(self):
        assert os.path.isfile(AARAV_VAL_JSON), (
            f"validation.json not found for aarav; run validation first"
        )
        data = _load_json(AARAV_VAL_JSON)
        missing = data.get("checks", {}).get("missing_bones", None)
        assert missing is not None, "missing_bones key absent from validation.json"
        assert missing == [], f"Aarav has missing bones: {missing}"

    def test_aanya_all_bones(self):
        assert os.path.isfile(AANYA_VAL_JSON), (
            f"validation.json not found for aanya; run validation first"
        )
        data = _load_json(AANYA_VAL_JSON)
        missing = data.get("checks", {}).get("missing_bones", None)
        assert missing is not None, "missing_bones key absent from validation.json"
        assert missing == [], f"Aanya has missing bones: {missing}"


# ===========================================================================
# Bone count tests (read from character.json)
# ===========================================================================


@_skip_no_blender
class TestBoneCount:
    """Verify armature_bones >= 20 as recorded in character.json."""

    def test_aarav_bone_count(self):
        assert os.path.isfile(AARAV_CHAR_JSON), (
            f"character.json not found for aarav"
        )
        data = _load_json(AARAV_CHAR_JSON)
        count = data["statistics"]["armature_bones"]
        assert count >= 20, (
            f"Aarav armature_bones={count}, expected >= 20"
        )

    def test_aanya_bone_count(self):
        assert os.path.isfile(AANYA_CHAR_JSON), (
            f"character.json not found for aanya"
        )
        data = _load_json(AANYA_CHAR_JSON)
        count = data["statistics"]["armature_bones"]
        assert count >= 20, (
            f"Aanya armature_bones={count}, expected >= 20"
        )


# ===========================================================================
# Pose application test
# ===========================================================================


@_skip_no_blender
class TestPoseApplication:
    """Apply a rotation to upper_arm_R and confirm it was stored correctly."""

    def test_pose_application(self):
        inline_script = (
            "import bpy, math\n"
            f"bpy.ops.wm.open_mainfile(filepath={AARAV_BLEND!r})\n"
            "arm_obj = bpy.data.objects.get('Aarav_Armature')\n"
            "if arm_obj is None:\n"
            "    print('POSE_FAIL: Aarav_Armature not found')\n"
            "    raise SystemExit(1)\n"
            "bpy.context.view_layer.objects.active = arm_obj\n"
            "bpy.ops.object.mode_set(mode='POSE')\n"
            "bone = arm_obj.pose.bones.get('upper_arm_R')\n"
            "if bone is None:\n"
            "    print('POSE_FAIL: upper_arm_R not found')\n"
            "    raise SystemExit(1)\n"
            "bone.rotation_mode = 'XYZ'\n"
            "target = -1.2\n"
            "bone.rotation_euler[0] = target\n"
            "bpy.context.view_layer.update()\n"
            "actual = bone.rotation_euler[0]\n"
            "if abs(actual - target) < 1e-4:\n"
            "    print('POSE_OK')\n"
            "else:\n"
            "    print(f'POSE_FAIL: expected {target}, got {actual}')\n"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(inline_script)
            tmp_path = tmp.name

        try:
            result = _run_blender(tmp_path, timeout=120)
            combined = result.stdout + result.stderr
            assert "POSE_OK" in combined, (
                f"Expected 'POSE_OK' in Blender output, got:\n{combined[-2000:]}"
            )
        finally:
            os.unlink(tmp_path)
