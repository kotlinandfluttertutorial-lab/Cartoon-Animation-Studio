"""System information collection for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations

import platform
import subprocess
import sys

import psutil

from studio.schemas import SystemInfo


def collect(blender_exe: str, ffmpeg_exe: str) -> SystemInfo:
    """Collect system information and return a SystemInfo model."""

    # CPU info
    cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True) or 0
    try:
        freq = psutil.cpu_freq()
        freq_ghz = f"{freq.max / 1000:.1f} GHz" if freq and freq.max else "unknown frequency"
    except Exception:
        freq_ghz = "unknown frequency"
    cpu_str = f"{platform.processor() or 'Unknown CPU'}, {cpu_count} cores, {freq_ghz}"

    # RAM
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)

    # GPU — try wmic on Windows; fallback to Unknown
    gpu_name = "Unknown"
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "path", "win32_VideoController", "get", "name"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip() and line.strip().lower() != "name"
            ]
            if lines:
                gpu_name = lines[0]
        except Exception:
            gpu_name = "Unknown"

    # Blender version
    blender_version = "Unknown"
    try:
        result = subprocess.run(
            [blender_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        for line in result.stdout.splitlines():
            if "Blender" in line:
                blender_version = line.strip()
                break
        if blender_version == "Unknown" and result.stdout.strip():
            blender_version = result.stdout.splitlines()[0].strip()
    except Exception as exc:
        blender_version = f"Error: {exc}"

    # FFmpeg version
    ffmpeg_version = "Unknown"
    try:
        result = subprocess.run(
            [ffmpeg_exe, "-version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        for line in result.stdout.splitlines():
            if "ffmpeg version" in line.lower():
                ffmpeg_version = line.strip()
                break
        if ffmpeg_version == "Unknown" and result.stdout.strip():
            ffmpeg_version = result.stdout.splitlines()[0].strip()
    except Exception as exc:
        ffmpeg_version = f"Error: {exc}"

    return SystemInfo(
        cpu=cpu_str,
        ram_gb=ram_gb,
        gpu=gpu_name,
        blender_version=blender_version,
        ffmpeg_version=ffmpeg_version,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
    )
