"""
test_stage4_3_dialogue.py — Stage 4.3 dialogue system tests.

Tests (10+ total):
  1.  phoneme_mapper module imports correctly
  2.  text_to_viseme_sequence returns non-empty list
  3.  All 7 viseme groups appear in a long text sequence
  4.  LipsyncData dataclass constructs correctly
  5.  save_lipsync / load_lipsync roundtrip preserves all fields
  6.  frame count matches fps * duration
  7.  expression_library contains all 6 emotions
  8.  apply_expression returns a saved state dict (pure-Python path)
  9.  restore_expression runs without error (pure-Python path)
  10. DialogueLine dataclass constructs with defaults
  11. PhonemeMapper.text_to_viseme_list returns valid viseme names
  12. text_to_viseme_sequence frame 1 is REST
  13. PhonemeMapper handles empty text gracefully
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

from studio.dialogue.phoneme_mapper import PhonemeMapper, text_to_viseme_sequence
from studio.dialogue.mouth_shapes import MouthShapes, VISEME_MOUTH_TRANSFORMS, VALID_VISEMES
from studio.dialogue.lipsync_generator import LipsyncData, generate_lipsync, save_lipsync, load_lipsync
from studio.dialogue.expression_library import (
    EXPRESSIONS, ExpressionLibrary, apply_expression, restore_expression
)
from studio.dialogue.dialogue_sequencer import DialogueLine

# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestPhonemeMapper(unittest.TestCase):
    """Tests 1-3, 11-13: PhonemeMapper and text_to_viseme_sequence."""

    def test_01_phoneme_mapper_imports(self):
        """phoneme_mapper module and PhonemeMapper class import correctly."""
        self.assertIsNotNone(PhonemeMapper)
        self.assertIsNotNone(text_to_viseme_sequence)
        self.assertTrue(hasattr(PhonemeMapper, "text_to_viseme_list"))

    def test_02_text_to_viseme_sequence_nonempty(self):
        """text_to_viseme_sequence returns a non-empty list for normal text."""
        seq = text_to_viseme_sequence("Hello world", 2.0, fps=24)
        self.assertIsInstance(seq, list)
        self.assertGreater(len(seq), 0)

    def test_03_all_seven_visemes_in_long_text(self):
        """All 7 viseme groups appear when processing a long, varied sentence."""
        text = (
            "The big brown fox jumps over the lazy dog. "
            "She says please and thank you very much. "
            "Will you come and play with me today? "
            "My name is Aarav and I am very happy to meet you."
        )
        seq = text_to_viseme_sequence(text, 10.0, fps=24)
        visemes_found = {v for _, v in seq}
        all_seven = {"REST", "MBP", "FV", "TD", "WQ", "OPEN", "EI"}
        # In a long enough sentence all 7 should appear
        missing = all_seven - visemes_found
        self.assertEqual(
            len(missing), 0,
            f"Missing visemes: {missing}. Found: {visemes_found}"
        )

    def test_11_text_to_viseme_list_valid_names(self):
        """PhonemeMapper.text_to_viseme_list returns only valid viseme names."""
        result = PhonemeMapper.text_to_viseme_list("Hello my name is Aanya")
        for v in result:
            self.assertIn(v, VALID_VISEMES, f"Invalid viseme: {v!r}")

    def test_12_sequence_frame_one_is_rest(self):
        """Frame 1 in text_to_viseme_sequence is always REST."""
        seq = text_to_viseme_sequence("say something", 2.0, fps=24)
        frame_dict = dict(seq)
        self.assertEqual(frame_dict.get(1), "REST")

    def test_13_empty_text_handled_gracefully(self):
        """Empty text returns a list with at least REST entries."""
        seq = text_to_viseme_sequence("", 1.0, fps=24)
        self.assertIsInstance(seq, list)
        self.assertGreater(len(seq), 0)
        for _, v in seq:
            self.assertIn(v, VALID_VISEMES)


class TestLipsyncData(unittest.TestCase):
    """Tests 4-6: LipsyncData dataclass and save/load roundtrip."""

    def test_04_lipsync_data_constructs(self):
        """LipsyncData dataclass accepts all required fields."""
        data = LipsyncData(
            fps=24,
            total_frames=48,
            character="Aarav",
            frames={1: "REST", 5: "OPEN", 10: "EI"},
            blink_frames=[24, 48],
            text="hello",
        )
        self.assertEqual(data.fps, 24)
        self.assertEqual(data.total_frames, 48)
        self.assertEqual(data.character, "Aarav")
        self.assertEqual(data.frames[5], "OPEN")

    def test_05_save_load_roundtrip(self):
        """save_lipsync / load_lipsync roundtrip preserves all data."""
        data = LipsyncData(
            fps=24,
            total_frames=72,
            character="Aanya",
            frames={1: "REST", 12: "MBP", 24: "FV", 36: "OPEN", 72: "REST"},
            blink_frames=[48, 96],
            text="play with me",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_lipsync.json")
            save_lipsync(data, path)
            self.assertTrue(os.path.isfile(path))

            loaded = load_lipsync(path)
            self.assertEqual(loaded.fps, data.fps)
            self.assertEqual(loaded.total_frames, data.total_frames)
            self.assertEqual(loaded.character, data.character)
            self.assertEqual(loaded.text, data.text)
            self.assertEqual(loaded.frames, data.frames)
            self.assertEqual(loaded.blink_frames, sorted(data.blink_frames))

    def test_06_frame_count_matches_fps_times_duration(self):
        """generate_lipsync total_frames == int(duration * fps)."""
        fps = 24
        duration_s = 3.0
        data = generate_lipsync("hello world", "Aarav", duration_s, fps=fps)
        expected = int(duration_s * fps)
        self.assertEqual(data.total_frames, expected)


class TestExpressionLibrary(unittest.TestCase):
    """Tests 7-9: expression library."""

    def test_07_expression_library_has_six_emotions(self):
        """EXPRESSIONS dict contains exactly 6 emotions."""
        expected = {"neutral", "happy", "surprised", "sad", "thinking", "excited"}
        self.assertEqual(set(EXPRESSIONS.keys()), expected)

    def test_08_apply_expression_returns_dict(self):
        """apply_expression (pure-Python) returns a dict as saved state."""
        saved = apply_expression("Aarav", "happy")
        self.assertIsInstance(saved, dict)

    def test_09_restore_expression_no_error(self):
        """restore_expression (pure-Python) runs without raising exceptions."""
        saved = apply_expression("Aanya", "surprised")
        # Should not raise
        restore_expression(saved)


class TestDialogueLine(unittest.TestCase):
    """Test 10: DialogueLine dataclass."""

    def test_10_dialogue_line_constructs(self):
        """DialogueLine dataclass constructs with and without optional fields."""
        line = DialogueLine(character="Aarav", text="Hello there!")
        self.assertEqual(line.character, "Aarav")
        self.assertEqual(line.text, "Hello there!")
        self.assertEqual(line.emotion, "neutral")
        self.assertEqual(line.start_frame, 1)
        self.assertEqual(line.audio_path, "")
        self.assertEqual(line.lipsync_path, "")

        line2 = DialogueLine(
            character="Aanya",
            text="Hi Aarav!",
            emotion="happy",
            start_frame=25,
        )
        self.assertEqual(line2.emotion, "happy")
        self.assertEqual(line2.start_frame, 25)


if __name__ == "__main__":
    unittest.main()
