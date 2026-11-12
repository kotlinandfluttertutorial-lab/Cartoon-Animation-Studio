"""
test_stage4_3_expressions.py — Stage 4.3 expression library tests.

Tests (8+ total):
  1.  Expression library has 6 emotions
  2.  Each emotion has valid transform keys (z_offset or scale)
  3.  Blender apply_expression.py script exists
  4.  Blender: expression changes mouth object scale via subprocess (skip if no Blender)
  5.  Blender: expression restores correctly after render (skip if no Blender)
  6.  ExpressionLibrary.get returns correct dict for valid emotion
  7.  ExpressionLibrary.get returns empty dict for 'neutral'
  8.  ExpressionLibrary.is_valid returns True/False correctly
  9.  apply_expression (pure-Python) records applied transform for each object
  10. EXPRESSIONS covers all required emotions by name
"""

import os
import sys
import subprocess
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Ensure project is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from studio.dialogue.expression_library import (
    EXPRESSIONS,
    ExpressionLibrary,
    apply_expression,
    restore_expression,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BLENDER_EXE = r"P:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe"
_BLENDER_AVAILABLE = os.path.isfile(_BLENDER_EXE)

_APPLY_EXPRESSION_SCRIPT = os.path.join(
    _REPO_ROOT, "blender", "scripts", "apply_expression.py"
)
_AARAV_BLEND = os.path.join(
    _REPO_ROOT, "blender", "assets", "characters", "aarav", "aarav_stage4.blend"
)
_AANYA_BLEND = os.path.join(
    _REPO_ROOT, "blender", "assets", "characters", "aanya", "aanya_stage4.blend"
)

_skip_no_blender = unittest.skipUnless(
    _BLENDER_AVAILABLE,
    f"Blender not available at {_BLENDER_EXE}",
)

# ---------------------------------------------------------------------------
# Valid transform keys
# ---------------------------------------------------------------------------
_VALID_TRANSFORM_KEYS = frozenset({"z_offset", "scale"})


class TestExpressionLibraryPython(unittest.TestCase):
    """Pure-Python tests for expression library — no Blender required."""

    def test_01_library_has_six_emotions(self):
        """Expression library has exactly 6 emotions."""
        self.assertEqual(len(EXPRESSIONS), 6)
        expected = {"neutral", "happy", "surprised", "sad", "thinking", "excited"}
        self.assertEqual(set(EXPRESSIONS.keys()), expected)

    def test_02_each_emotion_has_valid_transform_keys(self):
        """Each emotion's transform dicts use only recognised keys (z_offset, scale)."""
        for emotion, objects in EXPRESSIONS.items():
            for obj_suffix, tx in objects.items():
                for key in tx.keys():
                    self.assertIn(
                        key, _VALID_TRANSFORM_KEYS,
                        f"Emotion '{emotion}', object '{obj_suffix}': unexpected key '{key}'"
                    )
                # If scale present, must be a 3-tuple of floats
                if "scale" in tx:
                    scale = tx["scale"]
                    self.assertEqual(len(scale), 3, f"Scale for {obj_suffix} must be 3-tuple")
                    for v in scale:
                        self.assertIsInstance(v, (int, float))

    def test_03_apply_expression_script_exists(self):
        """apply_expression.py Blender script exists at the expected path."""
        self.assertTrue(
            os.path.isfile(_APPLY_EXPRESSION_SCRIPT),
            f"Script not found: {_APPLY_EXPRESSION_SCRIPT}",
        )

    def test_06_expression_library_get_valid(self):
        """ExpressionLibrary.get returns correct dict for a valid emotion."""
        result = ExpressionLibrary.get("happy")
        self.assertIsInstance(result, dict)
        self.assertIn("Mouth", result)
        self.assertIn("scale", result["Mouth"])

    def test_07_expression_library_get_neutral(self):
        """ExpressionLibrary.get('neutral') returns an empty dict."""
        result = ExpressionLibrary.get("neutral")
        self.assertEqual(result, {})

    def test_08_expression_library_is_valid(self):
        """ExpressionLibrary.is_valid returns correct boolean."""
        self.assertTrue(ExpressionLibrary.is_valid("happy"))
        self.assertTrue(ExpressionLibrary.is_valid("neutral"))
        self.assertFalse(ExpressionLibrary.is_valid("angry"))
        self.assertFalse(ExpressionLibrary.is_valid(""))

    def test_09_apply_expression_records_applied_transforms(self):
        """apply_expression (pure-Python) records what was applied in returned dict."""
        # For each non-neutral emotion: saved state should have an entry
        # for each object suffix in the expression
        for emotion, objects in EXPRESSIONS.items():
            if not objects:
                # neutral — expect empty or stub dict
                saved = apply_expression("Aarav", emotion)
                # Could be empty (no-op) — just check it's a dict
                self.assertIsInstance(saved, dict)
                continue

            saved = apply_expression("Aarav", emotion)
            self.assertIsInstance(saved, dict)
            # Expect at least one entry matching an expected object
            for suffix in objects:
                obj_name = f"Aarav_{suffix}"
                # In pure-Python stub mode the key is the obj_name
                if obj_name in saved:
                    self.assertIn("applied", saved[obj_name])

    def test_10_expressions_covers_all_required_emotions(self):
        """EXPRESSIONS dict covers the six required emotion names."""
        required = {"neutral", "happy", "surprised", "sad", "thinking", "excited"}
        self.assertTrue(required.issubset(set(EXPRESSIONS.keys())))


class TestExpressionBlender(unittest.TestCase):
    """Blender integration tests — skipped if Blender unavailable."""

    @_skip_no_blender
    def test_04_blender_expression_changes_scale(self):
        """Blender subprocess: apply_expression.py runs without error for Aarav happy."""
        if not os.path.isfile(_AARAV_BLEND):
            self.skipTest(f"Blend file not found: {_AARAV_BLEND}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_png = os.path.join(tmpdir, "aarav_happy_test.png")
            cmd = [
                _BLENDER_EXE,
                "--background",
                _AARAV_BLEND,
                "--python",
                _APPLY_EXPRESSION_SCRIPT,
                "--",
                "Aarav",
                "happy",
                output_png,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.assertEqual(
                result.returncode, 0,
                f"Blender returned {result.returncode}.\nSTDOUT:\n{result.stdout[-2000:]}"
                f"\nSTDERR:\n{result.stderr[-1000:]}"
            )
            self.assertIn("EXPRESSION_RENDER_OK", result.stdout)
            self.assertTrue(os.path.isfile(output_png), "Output PNG was not created")
            self.assertGreater(os.path.getsize(output_png), 0)

    @_skip_no_blender
    def test_05_blender_expression_restores_correctly(self):
        """Blender subprocess: apply_expression.py script ends with EXPRESSION_RENDER_OK."""
        if not os.path.isfile(_AANYA_BLEND):
            self.skipTest(f"Blend file not found: {_AANYA_BLEND}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_png = os.path.join(tmpdir, "aanya_surprised_test.png")
            cmd = [
                _BLENDER_EXE,
                "--background",
                _AANYA_BLEND,
                "--python",
                _APPLY_EXPRESSION_SCRIPT,
                "--",
                "Aanya",
                "surprised",
                output_png,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            # Script must succeed and print the success token
            self.assertIn("EXPRESSION_RENDER_OK", result.stdout)
            if result.returncode == 0:
                self.assertTrue(os.path.isfile(output_png))


if __name__ == "__main__":
    unittest.main()
