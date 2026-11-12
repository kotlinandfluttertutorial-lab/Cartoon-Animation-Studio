"""
test_stage4_3_lipsync.py — Stage 4.3 lip-sync generation tests.

Tests (8+ total):
  1.  generate_lipsync returns LipsyncData
  2.  frame 1 is always REST (pre-speech)
  3.  blink events present at correct intervals
  4.  all frame visemes in the data are valid names
  5.  JSON file is saved correctly (file exists, is valid JSON)
  6.  JSON loads back to equivalent LipsyncData
  7.  LipsyncData.get_viseme returns REST for unspecified frames
  8.  generate_lipsync with include_blinks=False has empty blink_frames
  9.  generate_lipsync respects fps parameter
  10. load_lipsync raises FileNotFoundError for missing files
"""

import os
import sys
import json
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Ensure project is importable
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from studio.dialogue.lipsync_generator import (
    LipsyncData, LipsyncGenerator, generate_lipsync, save_lipsync, load_lipsync
)
from studio.dialogue.mouth_shapes import VALID_VISEMES, BLINK_INTERVAL_FRAMES


class TestGenerateLipsync(unittest.TestCase):
    """Tests 1-5, 7-10: generate_lipsync function."""

    def test_01_returns_lipsync_data(self):
        """generate_lipsync returns a LipsyncData instance."""
        data = generate_lipsync("Hello world", "Aarav", 2.0)
        self.assertIsInstance(data, LipsyncData)
        self.assertEqual(data.character, "Aarav")

    def test_02_frame_one_is_rest(self):
        """Frame 1 in generated lipsync data is REST."""
        data = generate_lipsync("Say something", "Aanya", 3.0)
        self.assertEqual(data.frames.get(1), "REST")

    def test_03_blink_events_at_correct_intervals(self):
        """Blink events appear at BLINK_INTERVAL_FRAMES multiples."""
        # 5 seconds at 24 fps = 120 frames; blink at frame 96
        data = generate_lipsync("long sentence", "Aarav", 5.0, fps=24, include_blinks=True)
        expected_blinks = [
            f for f in range(BLINK_INTERVAL_FRAMES, data.total_frames + 1, BLINK_INTERVAL_FRAMES)
        ]
        self.assertEqual(data.blink_frames, expected_blinks)

    def test_04_all_frame_visemes_valid(self):
        """Every viseme stored in the frames dict is a valid viseme name."""
        data = generate_lipsync(
            "The quick brown fox jumps over the lazy dog", "Aarav", 4.0
        )
        for frame, viseme in data.frames.items():
            self.assertIn(
                viseme, VALID_VISEMES,
                f"Frame {frame} has invalid viseme: {viseme!r}"
            )

    def test_05_json_saved_correctly(self):
        """save_lipsync creates a valid JSON file."""
        data = generate_lipsync("hi there", "Aanya", 1.5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "lipsync.json")
            save_lipsync(data, path)
            self.assertTrue(os.path.isfile(path))
            # Validate it's parseable JSON
            with open(path, encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertIn("fps", parsed)
            self.assertIn("total_frames", parsed)
            self.assertIn("frames", parsed)
            self.assertIn("character", parsed)

    def test_06_json_loads_to_same_data(self):
        """load_lipsync produces data equivalent to what was saved."""
        data = generate_lipsync("we are playing", "Aarav", 2.5)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "ls.json")
            save_lipsync(data, path)
            loaded = load_lipsync(path)

        self.assertEqual(loaded.fps, data.fps)
        self.assertEqual(loaded.total_frames, data.total_frames)
        self.assertEqual(loaded.character, data.character)
        self.assertEqual(loaded.frames, data.frames)

    def test_07_get_viseme_defaults_to_rest(self):
        """LipsyncData.get_viseme returns REST for frames not in the dict."""
        data = LipsyncData(fps=24, total_frames=48, character="Aarav")
        data.frames = {1: "REST", 10: "OPEN"}
        self.assertEqual(data.get_viseme(99), "REST")
        self.assertEqual(data.get_viseme(10), "OPEN")

    def test_08_no_blinks_when_disabled(self):
        """generate_lipsync with include_blinks=False has empty blink_frames."""
        data = generate_lipsync("hello", "Aanya", 5.0, include_blinks=False)
        self.assertEqual(data.blink_frames, [])

    def test_09_fps_parameter_respected(self):
        """LipsyncData.fps reflects the fps parameter passed."""
        data = generate_lipsync("test text", "Aarav", 2.0, fps=12)
        self.assertEqual(data.fps, 12)
        self.assertEqual(data.total_frames, 24)  # 2.0 * 12

    def test_10_missing_file_raises(self):
        """load_lipsync raises FileNotFoundError for a missing path."""
        with self.assertRaises(FileNotFoundError):
            load_lipsync("/nonexistent/path/lipsync.json")


class TestLipsyncGenerator(unittest.TestCase):
    """Test LipsyncGenerator class interface."""

    def test_11_lipsync_generator_class(self):
        """LipsyncGenerator.generate returns LipsyncData."""
        data = LipsyncGenerator.generate("say hello", "Aanya", 2.0)
        self.assertIsInstance(data, LipsyncData)


if __name__ == "__main__":
    unittest.main()
