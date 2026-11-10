"""FFmpeg runner for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from studio.logger import get_logger


@dataclass
class FFmpegResult:
    success: bool
    exit_code: int
    output_path: str
    duration_seconds: float
    file_size_bytes: int
    ffprobe_info: dict
    error_message: str


class FFmpegRunner:
    """Converts PNG image sequences to MP4 and validates output via ffprobe."""

    def __init__(self, ffmpeg_exe: str, ffprobe_exe: str) -> None:
        self._ffmpeg_exe = ffmpeg_exe
        self._ffprobe_exe = ffprobe_exe
        self._logger = get_logger("ffmpeg")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def frames_to_mp4(
        self,
        frames_dir: str,
        output_path: str,
        fps: int = 12,
        crf: int = 23,
        preset: str = "medium",
        audio_path: Optional[str] = None,
    ) -> FFmpegResult:
        """Convert a directory of PNG frames to an MP4 file.

        Blender names frames starting at 0001 by default.  The method
        detects the actual starting number via glob and passes
        -start_number to FFmpeg accordingly.
        """
        if audio_path is not None:
            self._logger.warning(
                "audio_path was supplied ('%s') but audio mixing is not yet "
                "implemented in this stage.  The parameter is ignored.",
                audio_path,
            )

        frames_path = Path(frames_dir)
        if not frames_path.exists():
            return FFmpegResult(
                success=False,
                exit_code=-1,
                output_path=output_path,
                duration_seconds=0.0,
                file_size_bytes=0,
                ffprobe_info={},
                error_message=f"Frames directory not found: {frames_dir}",
            )

        # Detect frame numbering pattern
        png_files = sorted(frames_path.glob("*.png"))
        if not png_files:
            return FFmpegResult(
                success=False,
                exit_code=-1,
                output_path=output_path,
                duration_seconds=0.0,
                file_size_bytes=0,
                ffprobe_info={},
                error_message=f"No PNG files found in: {frames_dir}",
            )

        # Determine the filename pattern and start number
        # Examples handled:
        #   0001.png, 0002.png   -> %04d.png, start_number=1
        #   frame_0001.png, ...  -> frame_%04d.png, start_number=1
        import re
        first_name = png_files[0].stem  # e.g. "frame_0001" or "0001"
        match = re.match(r'^(.*?)(\d+)$', first_name)
        if match:
            prefix = match.group(1)       # e.g. "frame_" or ""
            digits = match.group(2)       # e.g. "0001"
            pad_width = len(digits)
            start_number = int(digits)
        else:
            # Fallback: no trailing digits; use as-is
            prefix = first_name
            pad_width = 4
            start_number = 0

        frame_pattern = str(frames_path / f"{prefix}%0{pad_width}d.png")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._ffmpeg_exe,
            "-y",
            "-framerate", str(fps),
            "-start_number", str(start_number),
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset,
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        self._logger.info("Running FFmpeg: %s", " ".join(cmd))
        start_time = time.monotonic()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            stdout_data, stderr_data = proc.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return FFmpegResult(
                success=False,
                exit_code=-9,
                output_path=output_path,
                duration_seconds=time.monotonic() - start_time,
                file_size_bytes=0,
                ffprobe_info={},
                error_message="FFmpeg timed out after 300 seconds",
            )
        except FileNotFoundError as exc:
            return FFmpegResult(
                success=False,
                exit_code=-1,
                output_path=output_path,
                duration_seconds=0.0,
                file_size_bytes=0,
                ffprobe_info={},
                error_message=str(exc),
            )

        duration = time.monotonic() - start_time

        # Log progress lines
        for line in stderr_data.splitlines():
            if line.startswith("frame="):
                self._logger.debug("FFmpeg progress: %s", line.strip())

        exit_code = proc.returncode
        success = exit_code == 0

        output_p = Path(output_path)
        file_size = output_p.stat().st_size if output_p.exists() else 0

        error_message = ""
        if not success:
            # Grab the last few lines of stderr for context
            stderr_lines = [l for l in stderr_data.splitlines() if l.strip()]
            error_message = "\n".join(stderr_lines[-5:]) if stderr_lines else "Unknown FFmpeg error"
            self._logger.error("FFmpeg failed (exit %d): %s", exit_code, error_message)
        else:
            self._logger.info(
                "FFmpeg completed in %.1fs, output=%s (%d bytes)",
                duration,
                output_path,
                file_size,
            )

        return FFmpegResult(
            success=success,
            exit_code=exit_code,
            output_path=output_path,
            duration_seconds=round(duration, 3),
            file_size_bytes=file_size,
            ffprobe_info={},
            error_message=error_message,
        )

    def validate_output(self, mp4_path: str) -> dict:
        """Run ffprobe on mp4_path and return parsed stream/format info.

        Raises ValueError if duration is 0 or the video codec is not h264.
        """
        cmd = [
            self._ffprobe_exe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            mp4_path,
        ]

        self._logger.debug("Running ffprobe: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise ValueError(f"ffprobe timed out for: {mp4_path}")
        except FileNotFoundError as exc:
            raise ValueError(f"ffprobe not found: {exc}")

        if result.returncode != 0:
            raise ValueError(
                f"ffprobe failed (exit {result.returncode}): {result.stderr.strip()}"
            )

        try:
            info = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ffprobe output is not valid JSON: {exc}") from exc

        # Validate codec
        video_streams = [
            s for s in info.get("streams", [])
            if s.get("codec_type") == "video"
        ]
        if not video_streams:
            raise ValueError(f"No video streams found in: {mp4_path}")

        codec_name = video_streams[0].get("codec_name", "").lower()
        if codec_name != "h264":
            raise ValueError(
                f"Expected h264 codec, got '{codec_name}' in: {mp4_path}"
            )

        # Validate duration
        duration_str = info.get("format", {}).get("duration", "0")
        try:
            duration_val = float(duration_str)
        except (ValueError, TypeError):
            duration_val = 0.0

        if duration_val <= 0:
            raise ValueError(f"Output file has zero or invalid duration: {mp4_path}")

        self._logger.info(
            "ffprobe validation passed: codec=%s, duration=%.2fs",
            codec_name,
            duration_val,
        )
        return info
