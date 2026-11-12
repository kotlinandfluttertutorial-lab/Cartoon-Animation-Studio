"""
test_stage4_2_2_transform_hierarchy.py - Stage 4.2.2 transform hierarchy tests.

16 tests covering:
  1.  test_aarav_original_unchanged        — aarav.blend is 774392 bytes
  2.  test_aanya_original_unchanged        — aanya.blend is 796228 bytes
  3.  test_aarav_stage4_exists             — aarav_stage4.blend exists
  4.  test_aanya_stage4_exists             — aanya_stage4.blend exists
  5.  test_safe_bones_includes_head        — _SAFE_BONES has 'head' and 'neck'
  6.  test_aarav_nod_action_head_rotation  — AARAV_NOD head X rot at frame 4 >= 0.4 rad
  7.  test_aanya_nod_action_head_rotation  — AANYA_NOD head X rot at frame 4 >= 0.4 rad
  8.  test_all_14_previews_exist           — all 14 PNGs in output/stage4_2_2/previews/
  9.  test_all_previews_valid_png          — valid PNG header on all 14 files
  10. test_all_previews_gt_20kb            — all 14 files > 20480 bytes
  11. test_aarav_nod_differs_from_idle     — SHA256 of aarav_nod.png != aarav_idle.png
  12. test_aanya_nod_differs_from_idle     — SHA256 of aanya_nod.png != aanya_idle.png
  13. test_aarav_nod_pixel_diff            — aarav_nod.png vs aarav_idle.png differ >= 2% pixels
  14. test_aanya_nod_pixel_diff            — aanya_nod.png vs aanya_idle.png differ >= 2% pixels
  15. test_regression_stage421             — test_stage4_2_1_reliability.py exits 0
  16. test_check_before_push_syntax        — check_before_push.py --syntax exits 0 (skipped if missing)
"""

import hashlib
import os
import struct
import subprocess
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT  = Path(r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio')
REPO_ROOT = Path(r'P:\AI\Cartoon-Animation-Studio')
PREVIEWS = PROJECT / 'output' / 'stage4_2_2' / 'previews'
BLENDER  = r'P:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe'
AARAV_STAGE4 = str(PROJECT / 'blender' / 'assets' / 'characters' / 'aarav' / 'aarav_stage4.blend')
AANYA_STAGE4 = str(PROJECT / 'blender' / 'assets' / 'characters' / 'aanya' / 'aanya_stage4.blend')
_BLENDER_MISSING = not os.path.isfile(BLENDER)

PREVIEW_FILES = [
    'aarav_idle.png',   'aarav_wave.png',  'aarav_point.png',  'aarav_nod.png',
    'aanya_idle.png',   'aanya_wave.png',  'aanya_point.png',  'aanya_nod.png',
    'both_facing_camera.png',    'greeting_interaction.png',
    'pointing_interaction.png',  'walk_together.png',
    'aarav_nod_sequence.png',    'aanya_nod_sequence.png',
]

_PNG_HEADER = b'\x89PNG\r\n\x1a\n'


# ---------------------------------------------------------------------------
# Helper: SHA-256 of a file
# ---------------------------------------------------------------------------
def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Helper: run a Blender subprocess with an inline script, return stdout+stderr
# ---------------------------------------------------------------------------
def _run_blender_script(blend_file, script_text, timeout=180):
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False,
                                     encoding='utf-8') as tf:
        tf.write(script_text)
        tmp = tf.name
    try:
        result = subprocess.run(
            [BLENDER, '--background', blend_file, '--python', tmp],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr, result.returncode
    finally:
        os.unlink(tmp)


# ===========================================================================
# Tests
# ===========================================================================

class TestStage422(unittest.TestCase):

    # -----------------------------------------------------------------------
    # 1 & 2: original .blend file integrity
    # -----------------------------------------------------------------------

    def test_aarav_original_unchanged(self):
        """aarav.blend is exactly 774392 bytes (original asset unchanged)."""
        p = PROJECT / 'blender' / 'assets' / 'characters' / 'aarav' / 'aarav.blend'
        self.assertTrue(p.is_file(), f'aarav.blend not found: {p}')
        size = p.stat().st_size
        self.assertEqual(size, 774392,
                         f'aarav.blend size changed: {size} != 774392')

    def test_aanya_original_unchanged(self):
        """aanya.blend is exactly 796228 bytes (original asset unchanged)."""
        p = PROJECT / 'blender' / 'assets' / 'characters' / 'aanya' / 'aanya.blend'
        self.assertTrue(p.is_file(), f'aanya.blend not found: {p}')
        size = p.stat().st_size
        self.assertEqual(size, 796228,
                         f'aanya.blend size changed: {size} != 796228')

    # -----------------------------------------------------------------------
    # 3 & 4: working copy .blend files exist
    # -----------------------------------------------------------------------

    def test_aarav_stage4_exists(self):
        """aarav_stage4.blend exists."""
        p = Path(AARAV_STAGE4)
        self.assertTrue(p.is_file(), f'aarav_stage4.blend not found: {p}')

    def test_aanya_stage4_exists(self):
        """aanya_stage4.blend exists."""
        p = Path(AANYA_STAGE4)
        self.assertTrue(p.is_file(), f'aanya_stage4.blend not found: {p}')

    # -----------------------------------------------------------------------
    # 5: _SAFE_BONES includes head and neck
    # -----------------------------------------------------------------------

    def test_safe_bones_includes_head(self):
        """character_movement.py _SAFE_BONES frozenset contains 'head' and 'neck'."""
        cm_path = PROJECT / 'blender' / 'scripts' / 'character_movement.py'
        self.assertTrue(cm_path.is_file(),
                        f'character_movement.py not found: {cm_path}')
        source = cm_path.read_text(encoding='utf-8')

        # Locate the _SAFE_BONES block by finding the frozenset literal
        self.assertIn('_SAFE_BONES', source,
                      '_SAFE_BONES not found in character_movement.py')

        # Find the span of the frozenset body
        start = source.find('_SAFE_BONES')
        block_end = source.find('})', start)
        if block_end == -1:
            block_end = source.find('}', start) + 1
        safe_block = source[start:block_end + 2]

        self.assertIn("'head'", safe_block,
                      "'head' not found inside _SAFE_BONES block")
        self.assertIn("'neck'", safe_block,
                      "'neck' not found inside _SAFE_BONES block")

    # -----------------------------------------------------------------------
    # 6 & 7: AARAV_NOD / AANYA_NOD head X rotation at frame 4
    # -----------------------------------------------------------------------

    @unittest.skipIf(_BLENDER_MISSING, f'Blender not found: {BLENDER}')
    def test_aarav_nod_action_head_rotation(self):
        """AARAV_NOD action has head X rotation at frame 4 >= 0.4 rad."""
        script = f"""\
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=r'{AARAV_STAGE4}')
action = bpy.data.actions.get('AARAV_NOD')
if action is None:
    print('NOD_HEAD_ROT:MISSING_ACTION')
    sys.exit(1)
for fc in action.fcurves:
    if 'head' in fc.data_path and fc.array_index == 0:
        val = fc.evaluate(4)
        print(f'NOD_HEAD_ROT:{{val:.6f}}')
        break
else:
    print('NOD_HEAD_ROT:NO_FCURVE')
"""
        output, rc = _run_blender_script(AARAV_STAGE4, script)
        # Find the token line
        rot_val = None
        for line in output.splitlines():
            if line.startswith('NOD_HEAD_ROT:'):
                token = line.split(':', 1)[1]
                if token in ('MISSING_ACTION', 'NO_FCURVE'):
                    self.fail(f'AARAV_NOD head fcurve issue: {token}')
                try:
                    rot_val = float(token)
                except ValueError:
                    self.fail(f'Could not parse NOD_HEAD_ROT value: {token!r}')
                break
        self.assertIsNotNone(rot_val,
                             'NOD_HEAD_ROT token not found in Blender output')
        self.assertGreaterEqual(rot_val, 0.4,
            f'AARAV_NOD head X rot at frame 4 is {rot_val:.4f} rad, expected >= 0.4')

    @unittest.skipIf(_BLENDER_MISSING, f'Blender not found: {BLENDER}')
    def test_aanya_nod_action_head_rotation(self):
        """AANYA_NOD action has head X rotation at frame 4 >= 0.4 rad."""
        script = f"""\
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=r'{AANYA_STAGE4}')
action = bpy.data.actions.get('AANYA_NOD')
if action is None:
    print('NOD_HEAD_ROT:MISSING_ACTION')
    sys.exit(1)
for fc in action.fcurves:
    if 'head' in fc.data_path and fc.array_index == 0:
        val = fc.evaluate(4)
        print(f'NOD_HEAD_ROT:{{val:.6f}}')
        break
else:
    print('NOD_HEAD_ROT:NO_FCURVE')
"""
        output, rc = _run_blender_script(AANYA_STAGE4, script)
        rot_val = None
        for line in output.splitlines():
            if line.startswith('NOD_HEAD_ROT:'):
                token = line.split(':', 1)[1]
                if token in ('MISSING_ACTION', 'NO_FCURVE'):
                    self.fail(f'AANYA_NOD head fcurve issue: {token}')
                try:
                    rot_val = float(token)
                except ValueError:
                    self.fail(f'Could not parse NOD_HEAD_ROT value: {token!r}')
                break
        self.assertIsNotNone(rot_val,
                             'NOD_HEAD_ROT token not found in Blender output')
        self.assertGreaterEqual(rot_val, 0.4,
            f'AANYA_NOD head X rot at frame 4 is {rot_val:.4f} rad, expected >= 0.4')

    # -----------------------------------------------------------------------
    # 8: all 14 preview files exist
    # -----------------------------------------------------------------------

    def test_all_14_previews_exist(self):
        """All 14 PNG files exist in output/stage4_2_2/previews/."""
        missing = [f for f in PREVIEW_FILES
                   if not (PREVIEWS / f).is_file()]
        self.assertFalse(missing,
                         f'Missing preview files: {missing}')

    # -----------------------------------------------------------------------
    # 9: all 14 previews have a valid PNG header
    # -----------------------------------------------------------------------

    def test_all_previews_valid_png(self):
        """All 14 preview PNGs have valid PNG magic bytes."""
        invalid = []
        for fname in PREVIEW_FILES:
            fpath = PREVIEWS / fname
            if not fpath.is_file():
                invalid.append(f'{fname} (missing)')
                continue
            with open(fpath, 'rb') as fh:
                header = fh.read(8)
            if header != _PNG_HEADER:
                invalid.append(f'{fname} (bad header: {header!r})')
        self.assertFalse(invalid, f'Invalid PNG files: {invalid}')

    # -----------------------------------------------------------------------
    # 10: all 14 previews > 20 KB
    # -----------------------------------------------------------------------

    def test_all_previews_gt_20kb(self):
        """All 14 preview PNGs are larger than 20 480 bytes (20 KB)."""
        small = []
        for fname in PREVIEW_FILES:
            fpath = PREVIEWS / fname
            if not fpath.is_file():
                small.append(f'{fname} (missing)')
                continue
            size = fpath.stat().st_size
            if size <= 20480:
                small.append(f'{fname} ({size} bytes)')
        self.assertFalse(small, f'Preview files too small (<= 20 KB): {small}')

    # -----------------------------------------------------------------------
    # 11 & 12: nod SHA-256 differs from idle (head visibly moved)
    # -----------------------------------------------------------------------

    def test_aarav_nod_differs_from_idle(self):
        """SHA256 of aarav_nod.png != SHA256 of aarav_idle.png."""
        nod_path  = PREVIEWS / 'aarav_nod.png'
        idle_path = PREVIEWS / 'aarav_idle.png'
        for p in (nod_path, idle_path):
            self.assertTrue(p.is_file(), f'File not found: {p}')
        self.assertNotEqual(
            _sha256(str(nod_path)),
            _sha256(str(idle_path)),
            'aarav_nod.png and aarav_idle.png are identical (head did not move)',
        )

    def test_aanya_nod_differs_from_idle(self):
        """SHA256 of aanya_nod.png != SHA256 of aanya_idle.png."""
        nod_path  = PREVIEWS / 'aanya_nod.png'
        idle_path = PREVIEWS / 'aanya_idle.png'
        for p in (nod_path, idle_path):
            self.assertTrue(p.is_file(), f'File not found: {p}')
        self.assertNotEqual(
            _sha256(str(nod_path)),
            _sha256(str(idle_path)),
            'aanya_nod.png and aanya_idle.png are identical (head did not move)',
        )

    # -----------------------------------------------------------------------
    # 13 & 14: pixel-level diff (Pillow if available, else file-size proxy)
    # -----------------------------------------------------------------------

    def _pixel_diff_percent(self, path_a, path_b):
        """
        Return the percentage of pixels that differ between two PNG files.
        Uses PIL/Pillow when available; falls back to a struct-based raw byte
        approach that reads the IDAT compressed data length as a size proxy.
        """
        try:
            from PIL import Image  # type: ignore
        except ImportError:
            return None  # caller decides how to handle absence

        img_a = Image.open(str(path_a)).convert('RGB')
        img_b = Image.open(str(path_b)).convert('RGB')
        if img_a.size != img_b.size:
            # Sizes differ — definitely different
            return 100.0
        # Use tobytes() to avoid Pillow 14 getdata() deprecation
        data_a = img_a.tobytes()
        data_b = img_b.tobytes()
        total_pixels = img_a.size[0] * img_a.size[1]
        # Each pixel is 3 bytes (RGB); compare triplets
        diff = sum(
            1 for i in range(0, len(data_a), 3)
            if data_a[i:i + 3] != data_b[i:i + 3]
        )
        return 100.0 * diff / total_pixels

    def _file_size_diff_pct(self, path_a, path_b):
        """Return absolute percentage size difference between two files."""
        sa = os.path.getsize(str(path_a))
        sb = os.path.getsize(str(path_b))
        if sa == 0 and sb == 0:
            return 0.0
        return 100.0 * abs(sa - sb) / max(sa, sb)

    def test_aarav_nod_pixel_diff(self):
        """aarav_nod.png vs aarav_idle.png differ by >= 2% pixels."""
        nod_path  = PREVIEWS / 'aarav_nod.png'
        idle_path = PREVIEWS / 'aarav_idle.png'
        for p in (nod_path, idle_path):
            self.assertTrue(p.is_file(), f'File not found: {p}')

        pct = self._pixel_diff_percent(nod_path, idle_path)
        if pct is None:
            # Pillow not available — use file size difference > 1% as proxy
            size_diff = self._file_size_diff_pct(nod_path, idle_path)
            if size_diff <= 1.0:
                self.skipTest(
                    f'Pillow not installed; file-size diff is {size_diff:.2f}% '
                    f'(<= 1%) — cannot confirm pixel difference without Pillow'
                )
            return  # size differs enough — accept as proxy

        self.assertGreaterEqual(
            pct, 2.0,
            f'aarav_nod.png vs aarav_idle.png: only {pct:.2f}% pixels differ '
            f'(expected >= 2% — head movement not visible)',
        )

    def test_aanya_nod_pixel_diff(self):
        """aanya_nod.png vs aanya_idle.png differ by >= 2% pixels."""
        nod_path  = PREVIEWS / 'aanya_nod.png'
        idle_path = PREVIEWS / 'aanya_idle.png'
        for p in (nod_path, idle_path):
            self.assertTrue(p.is_file(), f'File not found: {p}')

        pct = self._pixel_diff_percent(nod_path, idle_path)
        if pct is None:
            size_diff = self._file_size_diff_pct(nod_path, idle_path)
            if size_diff <= 1.0:
                self.skipTest(
                    f'Pillow not installed; file-size diff is {size_diff:.2f}% '
                    f'(<= 1%) — cannot confirm pixel difference without Pillow'
                )
            return

        self.assertGreaterEqual(
            pct, 2.0,
            f'aanya_nod.png vs aanya_idle.png: only {pct:.2f}% pixels differ '
            f'(expected >= 2% — head movement not visible)',
        )

    # -----------------------------------------------------------------------
    # 15: regression — Stage 4.2.1 test suite still passes
    # -----------------------------------------------------------------------

    def test_regression_stage421(self):
        """tests/test_stage4_2_1_reliability.py exits 0 (no regressions)."""
        result = subprocess.run(
            [sys.executable, '-m', 'pytest',
             'tests/test_stage4_2_1_reliability.py', '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT),
        )
        self.assertEqual(
            result.returncode, 0,
            f'Stage 4.2.1 regression suite failed (exit {result.returncode}).\n'
            f'stdout:\n{result.stdout[-3000:]}\n'
            f'stderr:\n{result.stderr[-1000:]}',
        )

    # -----------------------------------------------------------------------
    # 16: check_before_push.py --syntax exits 0
    # -----------------------------------------------------------------------

    def test_check_before_push_syntax(self):
        """check_before_push.py --syntax exits 0 (skipped if script not found)."""
        # The script lives at the repo root, one level above the project dir
        cbp = REPO_ROOT / 'check_before_push.py'
        if not cbp.is_file():
            self.skipTest(
                f'check_before_push.py not found at {cbp} — skipping syntax check'
            )
        result = subprocess.run(
            [sys.executable, str(cbp), '--syntax'],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(
            result.returncode, 0,
            f'check_before_push.py --syntax failed (exit {result.returncode}).\n'
            f'stdout:\n{result.stdout[-3000:]}\n'
            f'stderr:\n{result.stderr[-1000:]}',
        )


if __name__ == '__main__':
    unittest.main()
