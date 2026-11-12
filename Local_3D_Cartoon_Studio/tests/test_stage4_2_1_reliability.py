"""
test_stage4_2_1_reliability.py - Stage 4.2.1 reliability tests.

12 tests covering:
  - Original character file integrity
  - character_movement.py new API
  - All 12 preview PNG existence, PNG validity, and size
  - Gesture action presence (via Blender subprocess)
  - Regression checks for Stage 4.1 and 4.2 actions
  - Render script existence
"""

import os
import subprocess
import sys
import struct
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
_BLENDER_EXE = r'P:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe'
_AARAV_BLEND_ORIG = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aarav', 'aarav.blend')
_AANYA_BLEND_ORIG = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aanya', 'aanya.blend')
_AARAV_BLEND_STAGE4 = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aarav', 'aarav_stage4.blend')
_AANYA_BLEND_STAGE4 = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aanya', 'aanya_stage4.blend')
_PREVIEWS_DIR = os.path.join(_REPO_ROOT, 'output', 'stage4_2_1', 'previews')
_CHARACTER_MOVEMENT = os.path.join(_REPO_ROOT, 'blender', 'scripts', 'character_movement.py')
_RENDER_SCRIPT = os.path.join(_REPO_ROOT, 'blender', 'scripts', 'render_stage421_previews.py')

_PNG_HEADER = b'\x89PNG\r\n\x1a\n'

_ALL_12_PREVIEWS = [
    'aarav_idle.png',
    'aarav_wave.png',
    'aarav_point.png',
    'aarav_nod.png',
    'aanya_idle.png',
    'aanya_wave.png',
    'aanya_point.png',
    'aanya_nod.png',
    'both_facing_camera.png',
    'greeting_interaction.png',
    'pointing_interaction.png',
    'walk_together.png',
]


# ---------------------------------------------------------------------------
# Helper: run Blender subprocess to check actions
# ---------------------------------------------------------------------------

def _blender_check_actions(blend_file, action_names):
    """
    Run a Blender background process to verify action_names are in blend_file.
    Returns a dict: {action_name: bool}.
    """
    script_lines = [
        'import bpy',
        'import sys',
        f'names = {action_names!r}',
        'for n in names:',
        '    found = bpy.data.actions.get(n) is not None',
        '    print(f"ACTION_CHECK {n} " + ("FOUND" if found else "MISSING"))',
    ]
    script = '\n'.join(script_lines)

    # Write to temp file to avoid shell escaping issues
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script)
        tmp_script = f.name

    try:
        result = subprocess.run(
            [_BLENDER_EXE, '--background', blend_file, '--python', tmp_script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr
        findings = {}
        for line in output.splitlines():
            if line.startswith('ACTION_CHECK '):
                parts = line.split()
                if len(parts) >= 3:
                    findings[parts[1]] = (parts[2] == 'FOUND')
        return findings
    finally:
        os.unlink(tmp_script)


# ===========================================================================
# Tests
# ===========================================================================

class TestFileIntegrity:
    """Test 1 & 2: Original character files must be unchanged."""

    def test_aarav_orig_file_unchanged(self):
        """aarav.blend original file is exactly 774392 bytes."""
        assert os.path.isfile(_AARAV_BLEND_ORIG), f'File not found: {_AARAV_BLEND_ORIG}'
        size = os.path.getsize(_AARAV_BLEND_ORIG)
        assert size == 774392, f'aarav.blend size changed: {size} != 774392'

    def test_aanya_orig_file_unchanged(self):
        """aanya.blend original file is exactly 796228 bytes."""
        assert os.path.isfile(_AANYA_BLEND_ORIG), f'File not found: {_AANYA_BLEND_ORIG}'
        size = os.path.getsize(_AANYA_BLEND_ORIG)
        assert size == 796228, f'aanya.blend size changed: {size} != 796228'


class TestCharacterMovementAPI:
    """Tests 3 & 4: character_movement.py must have new API functions."""

    def test_character_movement_has_compute_rest_offsets(self):
        """character_movement.py defines compute_rest_offsets()."""
        assert os.path.isfile(_CHARACTER_MOVEMENT), f'Not found: {_CHARACTER_MOVEMENT}'
        with open(_CHARACTER_MOVEMENT, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'compute_rest_offsets' in content, \
            'compute_rest_offsets not found in character_movement.py'

    def test_character_movement_has_safe_bones(self):
        """character_movement.py defines _SAFE_BONES frozenset."""
        assert os.path.isfile(_CHARACTER_MOVEMENT), f'Not found: {_CHARACTER_MOVEMENT}'
        with open(_CHARACTER_MOVEMENT, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '_SAFE_BONES' in content, \
            '_SAFE_BONES not found in character_movement.py'


class TestPreviewFiles:
    """Tests 5, 6, 7: All 12 preview PNGs must exist, be valid PNGs, and >20 KB."""

    def test_all_12_previews_exist(self):
        """All 12 preview PNGs exist in output/stage4_2_1/previews/."""
        missing = []
        for fname in _ALL_12_PREVIEWS:
            fpath = os.path.join(_PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                missing.append(fname)
        assert not missing, f'Missing preview files: {missing}'

    def test_all_12_previews_are_valid_pngs(self):
        """All 12 preview PNGs have a valid PNG header."""
        invalid = []
        for fname in _ALL_12_PREVIEWS:
            fpath = os.path.join(_PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                invalid.append(f'{fname} (missing)')
                continue
            with open(fpath, 'rb') as f:
                header = f.read(8)
            if header != _PNG_HEADER:
                invalid.append(f'{fname} (bad header: {header!r})')
        assert not invalid, f'Invalid PNG files: {invalid}'

    def test_all_12_previews_gt_20kb(self):
        """All 12 preview PNGs are larger than 20 KB."""
        small = []
        for fname in _ALL_12_PREVIEWS:
            fpath = os.path.join(_PREVIEWS_DIR, fname)
            if not os.path.isfile(fpath):
                small.append(f'{fname} (missing)')
                continue
            size = os.path.getsize(fpath)
            if size <= 20480:
                small.append(f'{fname} ({size} bytes)')
        assert not small, f'Preview files too small (<= 20 KB): {small}'


class TestGestureActions:
    """Tests 8–11: Gesture actions present in stage4 blend files."""

    def test_aarav_gesture_actions_present(self):
        """AARAV_WAVE, AARAV_POINT, AARAV_NOD, AARAV_GREETING present in aarav_stage4.blend."""
        required = ['AARAV_WAVE', 'AARAV_POINT', 'AARAV_NOD', 'AARAV_GREETING']
        findings = _blender_check_actions(_AARAV_BLEND_STAGE4, required)
        missing = [n for n in required if not findings.get(n, False)]
        assert not missing, f'Missing Aarav gesture actions: {missing}'

    def test_aanya_gesture_actions_present(self):
        """AANYA_WAVE, AANYA_POINT, AANYA_NOD, AANYA_GREETING present in aanya_stage4.blend."""
        required = ['AANYA_WAVE', 'AANYA_POINT', 'AANYA_NOD', 'AANYA_GREETING']
        findings = _blender_check_actions(_AANYA_BLEND_STAGE4, required)
        missing = [n for n in required if not findings.get(n, False)]
        assert not missing, f'Missing Aanya gesture actions: {missing}'

    def test_aarav_regression_actions(self):
        """AARAV_IDLE and AARAV_WALK still present in aarav_stage4.blend."""
        required = ['AARAV_IDLE', 'AARAV_WALK']
        findings = _blender_check_actions(_AARAV_BLEND_STAGE4, required)
        missing = [n for n in required if not findings.get(n, False)]
        assert not missing, f'Missing Aarav regression actions: {missing}'

    def test_aanya_regression_actions(self):
        """AANYA_IDLE and AANYA_WALK still present in aanya_stage4.blend."""
        required = ['AANYA_IDLE', 'AANYA_WALK']
        findings = _blender_check_actions(_AANYA_BLEND_STAGE4, required)
        missing = [n for n in required if not findings.get(n, False)]
        assert not missing, f'Missing Aanya regression actions: {missing}'


class TestRenderScript:
    """Test 12: render_stage421_previews.py exists."""

    def test_render_stage421_script_exists(self):
        """render_stage421_previews.py exists in blender/scripts/."""
        assert os.path.isfile(_RENDER_SCRIPT), \
            f'render_stage421_previews.py not found at {_RENDER_SCRIPT}'
