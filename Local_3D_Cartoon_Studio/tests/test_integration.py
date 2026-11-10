"""Integration tests — require real Blender and FFmpeg executables."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.blender_runner import BlenderRunner
from studio.ffmpeg_runner import FFmpegRunner
from studio.logger import configure_logging

BLENDER_EXE = r"p:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe"
FFMPEG_EXE = (
    r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
)
FFPROBE_EXE = (
    r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"
)
SMOKE_TEST_SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "blender"
    / "scripts"
    / "smoke_test.py"
)

_blender_available = Path(BLENDER_EXE).exists()
_ffmpeg_available = Path(FFMPEG_EXE).exists()

_smoke_frames_dir: str | None = None  # shared between tests in this module


@unittest.skipUnless(_blender_available, f"Blender not found at {BLENDER_EXE}")
class TestRealBlenderSmokeTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="stage1_integration_")
        configure_logging(Path(self._tmpdir) / "logs")

    def test_real_blender_smoke_test(self):
        """Run the actual smoke test script and assert 3 PNG frames."""
        global _smoke_frames_dir

        runner = BlenderRunner(BLENDER_EXE, timeout=300)
        config = {
            "output_dir": self._tmpdir,
            "width": 640,
            "height": 360,
            "engine": "BLENDER_WORKBENCH",
        }

        result = runner.run(SMOKE_TEST_SCRIPT, config)

        # Store the frames dir for other tests to use
        frames_dir = Path(self._tmpdir) / "smoke_test"
        _smoke_frames_dir = str(frames_dir)

        self.assertTrue(
            result.success,
            f"Blender smoke test failed.\n"
            f"exit_code={result.exit_code}\n"
            f"stderr={result.stderr[-2000:]}\n"
            f"stdout={result.stdout[-2000:]}",
        )
        pngs = list(frames_dir.glob("*.png"))
        self.assertGreaterEqual(
            len(pngs),
            3,
            f"Expected at least 3 PNG frames in {frames_dir}, got {len(pngs)}",
        )


@unittest.skipUnless(
    _blender_available and _ffmpeg_available,
    "Blender or FFmpeg not available",
)
class TestRealFFmpegConversion(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="stage1_ffmpeg_")
        configure_logging(Path(self._tmpdir) / "logs")

    def _ensure_frames(self) -> str:
        """Run the smoke test to get real frames if not already done."""
        global _smoke_frames_dir

        if _smoke_frames_dir and Path(_smoke_frames_dir).exists():
            pngs = list(Path(_smoke_frames_dir).glob("*.png"))
            if len(pngs) >= 3:
                return _smoke_frames_dir

        # Run smoke test into our own temp dir
        runner = BlenderRunner(BLENDER_EXE, timeout=300)
        config = {
            "output_dir": self._tmpdir,
            "width": 640,
            "height": 360,
            "engine": "BLENDER_WORKBENCH",
        }
        result = runner.run(SMOKE_TEST_SCRIPT, config)
        self.assertTrue(result.success, f"Blender smoke test prerequisite failed: {result.stderr[-500:]}")
        frames_dir = Path(self._tmpdir) / "smoke_test"
        _smoke_frames_dir = str(frames_dir)
        return str(frames_dir)

    def test_real_ffmpeg_conversion(self):
        """frames_to_mp4 produces an MP4 that exists and is > 0 bytes."""
        frames_dir = self._ensure_frames()
        output_mp4 = str(Path(self._tmpdir) / "smoke_test.mp4")

        ff_runner = FFmpegRunner(FFMPEG_EXE, FFPROBE_EXE)
        ff_result = ff_runner.frames_to_mp4(frames_dir, output_mp4, fps=12)

        self.assertTrue(
            ff_result.success,
            f"FFmpeg failed: {ff_result.error_message}",
        )
        self.assertTrue(Path(output_mp4).exists(), "Output MP4 does not exist")
        self.assertGreater(Path(output_mp4).stat().st_size, 0, "Output MP4 is empty")

    def test_real_validate_mp4(self):
        """validate_output on the produced MP4 confirms h264 codec."""
        frames_dir = self._ensure_frames()
        output_mp4 = str(Path(self._tmpdir) / "smoke_validate.mp4")

        ff_runner = FFmpegRunner(FFMPEG_EXE, FFPROBE_EXE)
        ff_result = ff_runner.frames_to_mp4(frames_dir, output_mp4, fps=12)
        self.assertTrue(ff_result.success, f"FFmpeg failed: {ff_result.error_message}")

        info = ff_runner.validate_output(output_mp4)
        video_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
        self.assertTrue(len(video_streams) > 0, "No video streams found")
        self.assertEqual(video_streams[0]["codec_name"], "h264")


if __name__ == "__main__":
    unittest.main()
