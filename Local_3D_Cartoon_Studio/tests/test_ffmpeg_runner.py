"""Unit tests for ffmpeg_runner.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.ffmpeg_runner import FFmpegRunner, FFmpegResult

FAKE_FFMPEG = r"C:\fake\ffmpeg.exe"
FAKE_FFPROBE = r"C:\fake\ffprobe.exe"


def _make_runner() -> FFmpegRunner:
    return FFmpegRunner(ffmpeg_exe=FAKE_FFMPEG, ffprobe_exe=FAKE_FFPROBE)


def _mock_popen(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    mock_proc = MagicMock()
    mock_proc.returncode = returncode
    mock_proc.communicate.return_value = (stdout, stderr)
    return mock_proc


class TestFramesToMp4Command(unittest.TestCase):
    def test_frames_to_mp4_command(self):
        """Command must include -framerate, libx264, -pix_fmt yuv420p."""
        runner = _make_runner()

        captured_cmd: list = []

        def fake_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return _mock_popen(
                returncode=0,
                stderr="frame=  3 fps=12.0 ...",
            )

        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            # Create dummy PNG files
            (frames_dir / "0001.png").write_bytes(b"PNG")
            (frames_dir / "0002.png").write_bytes(b"PNG")
            (frames_dir / "0003.png").write_bytes(b"PNG")

            output_mp4 = str(frames_dir / "out.mp4")
            # Create a fake output file so stat() doesn't fail
            (frames_dir / "out.mp4").write_bytes(b"MP4")

            with patch("subprocess.Popen", side_effect=fake_popen):
                runner.frames_to_mp4(str(frames_dir), output_mp4, fps=12)

        self.assertIn("-framerate", captured_cmd)
        self.assertIn("libx264", captured_cmd)
        self.assertIn("-pix_fmt", captured_cmd)
        self.assertIn("yuv420p", captured_cmd)
        self.assertIn(FAKE_FFMPEG, captured_cmd)


class TestAudioStubWarning(unittest.TestCase):
    def test_audio_stub_warning(self):
        """Passing audio_path logs a warning but does not add it to the command."""
        runner = _make_runner()
        captured_cmd: list = []

        def fake_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            return _mock_popen(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            (frames_dir / "0001.png").write_bytes(b"PNG")
            output_mp4 = str(frames_dir / "out.mp4")
            (frames_dir / "out.mp4").write_bytes(b"MP4")

            with patch("subprocess.Popen", side_effect=fake_popen):
                import logging
                with self.assertLogs("studio.ffmpeg", level="WARNING") as log_ctx:
                    runner.frames_to_mp4(
                        str(frames_dir),
                        output_mp4,
                        audio_path=r"C:\fake\audio.wav",
                    )

        self.assertTrue(
            any("audio" in msg.lower() for msg in log_ctx.output),
            "Expected a warning about audio_path",
        )
        self.assertNotIn(r"C:\fake\audio.wav", captured_cmd)


class TestValidateOutputGood(unittest.TestCase):
    def test_validate_output_good(self):
        """h264 codec with valid duration does not raise."""
        runner = _make_runner()
        ffprobe_output = json.dumps({
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
            "format": {"duration": "5.0"},
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ffprobe_output
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            info = runner.validate_output(r"C:\fake\output.mp4")

        self.assertIn("streams", info)


class TestValidateOutputBadCodec(unittest.TestCase):
    def test_validate_output_bad_codec(self):
        """Non-h264 codec raises ValueError."""
        runner = _make_runner()
        ffprobe_output = json.dumps({
            "streams": [{"codec_type": "video", "codec_name": "mpeg4"}],
            "format": {"duration": "5.0"},
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ffprobe_output
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with self.assertRaises(ValueError) as ctx:
                runner.validate_output(r"C:\fake\output.mp4")

        self.assertIn("mpeg4", str(ctx.exception).lower())


class TestValidateOutputZeroDuration(unittest.TestCase):
    def test_validate_output_zero_duration(self):
        """Duration of 0 raises ValueError."""
        runner = _make_runner()
        ffprobe_output = json.dumps({
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
            "format": {"duration": "0"},
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ffprobe_output
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with self.assertRaises(ValueError) as ctx:
                runner.validate_output(r"C:\fake\output.mp4")

        self.assertIn("duration", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
