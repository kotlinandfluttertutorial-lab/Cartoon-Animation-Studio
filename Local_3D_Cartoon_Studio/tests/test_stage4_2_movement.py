"""
test_stage4_2_movement.py - Automated tests for Stage 4.2 implementation.

Tests (20 total):
  1-4:   Stage 4.1 regression — IDLE/WALK actions still present
  5-6:   Original character files unchanged (byte sizes)
  7-9:   Script files exist
  10-13: 8 preview PNGs exist, 640×360, >20KB, valid PNG signature
  14-19: Gesture actions exist in blend files (Blender subprocess per file)
  20:    All 4 report files exist

Blender exe: p:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe
"""

import os
import struct
import subprocess
import sys
import unittest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

BLENDER_EXE = r'p:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe'
BLENDER_AVAILABLE = os.path.isfile(BLENDER_EXE)

AARAV_BLEND = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aarav', 'aarav_stage4.blend')
AANYA_BLEND = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aanya', 'aanya_stage4.blend')
AARAV_ORIG  = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aarav', 'aarav.blend')
AANYA_ORIG  = os.path.join(_REPO_ROOT, 'blender', 'assets', 'characters', 'aanya', 'aanya.blend')

SCRIPTS_DIR = os.path.join(_REPO_ROOT, 'blender', 'scripts')
OUTPUT_DIR  = os.path.join(_REPO_ROOT, 'output', 'stage4_2', 'previews')
REPORTS_DIR = os.path.join(_REPO_ROOT, 'reports')

PREVIEW_FILES = [
    'aarav_wave.png',
    'aanya_wave.png',
    'aarav_point.png',
    'aanya_nod.png',
    'greeting_interaction.png',
    'walk_together.png',
    'both_facing_camera.png',
    'pointing_interaction.png',
]

REPORT_FILES = [
    'stage4_2_movement_system_report.md',
    'stage4_2_gesture_library_report.md',
    'stage4_2_interaction_validation_report.md',
    'stage4_2_playback_validation_report.md',
]

# ---------------------------------------------------------------------------
# Blender helper: run a snippet and return stdout
# ---------------------------------------------------------------------------

def _blender_check_actions(blend_file, action_names):
    """
    Use a Blender subprocess to check whether all action_names are present.
    Returns (found: set, missing: set).
    """
    names_repr = repr(action_names)
    script = f"""
import sys, bpy
bpy.ops.wm.open_mainfile(filepath={blend_file!r})
want = {names_repr}
found = set(a.name for a in bpy.data.actions)
for n in want:
    if n in found:
        print('FOUND:' + n)
    else:
        print('MISSING:' + n)
sys.exit(0)
"""
    tmp = os.path.join(os.environ.get('TEMP', '/tmp'), '_check_actions.py')
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(script)

    result = subprocess.run(
        [BLENDER_EXE, '--background', '--python', tmp],
        capture_output=True, text=True, timeout=120
    )
    found = set()
    missing = set()
    for line in result.stdout.splitlines():
        if line.startswith('FOUND:'):
            found.add(line[6:])
        elif line.startswith('MISSING:'):
            missing.add(line[8:])
    return found, missing


# ===========================================================================
# Tests
# ===========================================================================

class TestStage41Regression(unittest.TestCase):
    """Tests 1-4: Stage 4.1 actions still present."""

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_stage41_regression_aarav_idle(self):
        """Test 1: AARAV_IDLE still present in aarav_stage4.blend."""
        found, missing = _blender_check_actions(AARAV_BLEND, ['AARAV_IDLE'])
        self.assertIn('AARAV_IDLE', found, 'AARAV_IDLE missing from aarav_stage4.blend')

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_stage41_regression_aarav_walk(self):
        """Test 2: AARAV_WALK still present in aarav_stage4.blend."""
        found, missing = _blender_check_actions(AARAV_BLEND, ['AARAV_WALK'])
        self.assertIn('AARAV_WALK', found, 'AARAV_WALK missing from aarav_stage4.blend')

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_stage41_regression_aanya_idle(self):
        """Test 3: AANYA_IDLE still present in aanya_stage4.blend."""
        found, missing = _blender_check_actions(AANYA_BLEND, ['AANYA_IDLE'])
        self.assertIn('AANYA_IDLE', found, 'AANYA_IDLE missing from aanya_stage4.blend')

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_stage41_regression_aanya_walk(self):
        """Test 4: AANYA_WALK still present in aanya_stage4.blend."""
        found, missing = _blender_check_actions(AANYA_BLEND, ['AANYA_WALK'])
        self.assertIn('AANYA_WALK', found, 'AANYA_WALK missing from aanya_stage4.blend')


class TestOriginalFilesUnchanged(unittest.TestCase):
    """Tests 5-6: Original character files unchanged."""

    def test_original_aarav_unchanged(self):
        """Test 5: aarav.blend is 774392 bytes."""
        self.assertTrue(os.path.isfile(AARAV_ORIG), f'aarav.blend not found: {AARAV_ORIG}')
        size = os.path.getsize(AARAV_ORIG)
        self.assertEqual(size, 774392, f'aarav.blend size changed: expected 774392, got {size}')

    def test_original_aanya_unchanged(self):
        """Test 6: aanya.blend is 796228 bytes."""
        self.assertTrue(os.path.isfile(AANYA_ORIG), f'aanya.blend not found: {AANYA_ORIG}')
        size = os.path.getsize(AANYA_ORIG)
        self.assertEqual(size, 796228, f'aanya.blend size changed: expected 796228, got {size}')


class TestScriptFilesExist(unittest.TestCase):
    """Tests 7-9: Required script files exist."""

    def test_character_movement_script_exists(self):
        """Test 7: character_movement.py exists."""
        path = os.path.join(SCRIPTS_DIR, 'character_movement.py')
        self.assertTrue(os.path.isfile(path), f'character_movement.py not found: {path}')

    def test_gesture_library_script_exists(self):
        """Test 8: gesture_library.py exists."""
        path = os.path.join(SCRIPTS_DIR, 'gesture_library.py')
        self.assertTrue(os.path.isfile(path), f'gesture_library.py not found: {path}')

    def test_render_script_exists(self):
        """Test 9: render_stage42_previews.py exists."""
        path = os.path.join(SCRIPTS_DIR, 'render_stage42_previews.py')
        self.assertTrue(os.path.isfile(path), f'render_stage42_previews.py not found: {path}')


class TestPreviewPNGs(unittest.TestCase):
    """Tests 10-13: Preview PNG files."""

    def _all_png_paths(self):
        return [os.path.join(OUTPUT_DIR, f) for f in PREVIEW_FILES]

    def test_all_8_previews_exist(self):
        """Test 10: All 8 preview PNGs exist."""
        missing = []
        for f in PREVIEW_FILES:
            path = os.path.join(OUTPUT_DIR, f)
            if not os.path.isfile(path):
                missing.append(f)
        self.assertEqual(missing, [], f'Missing previews: {missing}')

    def test_all_8_previews_640x360(self):
        """Test 11: All 8 PNGs are 640×360."""
        for f in PREVIEW_FILES:
            path = os.path.join(OUTPUT_DIR, f)
            if not os.path.isfile(path):
                self.skipTest(f'File missing: {f}')
            with open(path, 'rb') as fh:
                # PNG IHDR: 8-byte sig + 4-byte length + 4-byte 'IHDR' + 4W + 4H
                data = fh.read(24)
            if len(data) < 24:
                self.fail(f'{f}: file too small to read PNG dimensions')
            # Width at offset 16, height at 20 (big-endian 32-bit)
            w = struct.unpack('>I', data[16:20])[0]
            h = struct.unpack('>I', data[20:24])[0]
            self.assertEqual(w, 640, f'{f}: width={w}, expected 640')
            self.assertEqual(h, 360, f'{f}: height={h}, expected 360')

    def test_all_8_previews_above_20kb(self):
        """Test 12: All 8 PNGs are > 20KB."""
        for f in PREVIEW_FILES:
            path = os.path.join(OUTPUT_DIR, f)
            if not os.path.isfile(path):
                self.skipTest(f'File missing: {f}')
            size = os.path.getsize(path)
            self.assertGreater(size, 20480, f'{f}: {size} bytes, expected > 20480')

    def test_all_8_previews_valid_png(self):
        """Test 13: All 8 PNGs have valid PNG signature."""
        PNG_SIG = b'\x89PNG\r\n\x1a\n'
        for f in PREVIEW_FILES:
            path = os.path.join(OUTPUT_DIR, f)
            if not os.path.isfile(path):
                self.skipTest(f'File missing: {f}')
            with open(path, 'rb') as fh:
                sig = fh.read(8)
            self.assertEqual(sig, PNG_SIG, f'{f}: invalid PNG signature')


class TestGestureActionsAarav(unittest.TestCase):
    """Tests 14-15-16-18: Aarav gesture actions exist (single Blender call)."""

    @classmethod
    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def setUpClass(cls):
        cls.found, cls.missing = _blender_check_actions(
            AARAV_BLEND,
            ['AARAV_WAVE', 'AARAV_POINT', 'AARAV_GREETING']
        )

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_aarav_wave_action_exists(self):
        """Test 14: AARAV_WAVE action in aarav_stage4.blend."""
        self.assertIn('AARAV_WAVE', self.found)

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_aarav_point_action_exists(self):
        """Test 16: AARAV_POINT action in aarav_stage4.blend."""
        self.assertIn('AARAV_POINT', self.found)

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_aarav_greeting_action_exists(self):
        """Test 18: AARAV_GREETING action in aarav_stage4.blend."""
        self.assertIn('AARAV_GREETING', self.found)


class TestGestureActionsAanya(unittest.TestCase):
    """Tests 15-17-19: Aanya gesture actions exist (single Blender call)."""

    @classmethod
    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def setUpClass(cls):
        cls.found, cls.missing = _blender_check_actions(
            AANYA_BLEND,
            ['AANYA_WAVE', 'AANYA_NOD', 'AANYA_GREETING']
        )

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_aanya_wave_action_exists(self):
        """Test 15: AANYA_WAVE action in aanya_stage4.blend."""
        self.assertIn('AANYA_WAVE', self.found)

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_aanya_nod_action_exists(self):
        """Test 17: AANYA_NOD action in aanya_stage4.blend."""
        self.assertIn('AANYA_NOD', self.found)

    @unittest.skipUnless(BLENDER_AVAILABLE, 'Blender exe not found')
    def test_aanya_greeting_action_exists(self):
        """Test 19: AANYA_GREETING action in aanya_stage4.blend."""
        self.assertIn('AANYA_GREETING', self.found)


class TestReportFiles(unittest.TestCase):
    """Test 20: All 4 report files exist."""

    def test_all_reports_exist(self):
        """Test 20: All 4 Stage 4.2 report files exist."""
        missing = []
        for f in REPORT_FILES:
            path = os.path.join(REPORTS_DIR, f)
            if not os.path.isfile(path):
                missing.append(f)
        self.assertEqual(missing, [], f'Missing reports: {missing}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
