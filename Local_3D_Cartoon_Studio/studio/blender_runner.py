"""Blender subprocess runner for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import psutil

from studio.logger import get_logger


@dataclass
class BlenderResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    peak_memory_mb: float
    frames_rendered: int
    error_details: list[str]


class BlenderRunner:
    """Runs Blender in background mode with a supplied Python script."""

    def __init__(self, blender_exe: str, timeout: int = 3600) -> None:
        self._blender_exe = blender_exe
        self._default_timeout = timeout
        self._logger = get_logger("blender")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def run(
        self,
        script_path: str,
        config_dict: dict,
        timeout: int | None = None,
    ) -> BlenderResult:
        """Run a Blender Python script with the given config_dict.

        config_dict is written to a temp JSON file and its path is passed
        via the BLENDER_CONFIG_PATH environment variable.
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout
        self._logger.info("Starting Blender run: script=%s", script_path)

        # Write config to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump(config_dict, tmp, indent=2)
            tmp_config_path = tmp.name

        try:
            return self._execute(
                script_path=script_path,
                config_path=tmp_config_path,
                timeout=effective_timeout,
            )
        finally:
            try:
                os.unlink(tmp_config_path)
            except OSError:
                pass

    def detect_render_errors(self, stdout: str, stderr: str) -> list[str]:
        """Return lines containing known error keywords from stdout+stderr."""
        error_keywords = ("Error", "Traceback", "CANCEL", "Exception", "Fatal")
        combined = (stdout + "\n" + stderr).splitlines()
        return [
            line for line in combined
            if any(kw in line for kw in error_keywords)
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(
        self,
        script_path: str,
        config_path: str,
        timeout: int,
    ) -> BlenderResult:
        cmd = [
            self._blender_exe,
            "--background",
            "--factory-startup",
            "--python",
            script_path,
        ]

        # Inherit environment and inject config path
        env = os.environ.copy()
        env["BLENDER_CONFIG_PATH"] = config_path

        self._logger.debug("Command: %s", " ".join(cmd))
        self._logger.debug("BLENDER_CONFIG_PATH: %s", config_path)

        start_time = time.monotonic()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            return BlenderResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_seconds=0.0,
                peak_memory_mb=0.0,
                frames_rendered=0,
                error_details=[str(exc)],
            )

        # Memory monitor thread
        stop_monitor = threading.Event()
        peak_mb_holder: list[float] = [0.0]

        def _monitor_memory() -> None:
            try:
                ps_proc = psutil.Process(proc.pid)
                while not stop_monitor.is_set():
                    try:
                        raw_rss = ps_proc.memory_info().rss
                        rss = float(raw_rss) / (1024 * 1024)
                        if rss > peak_mb_holder[0]:
                            peak_mb_holder[0] = rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
                    except (TypeError, ValueError):
                        break
                    time.sleep(0.5)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception:
                pass

        monitor_thread = threading.Thread(target=_monitor_memory, daemon=True)
        monitor_thread.start()

        timed_out = False
        try:
            stdout_data, stderr_data = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._logger.warning("Blender process timed out after %s seconds", timeout)
            try:
                proc.kill()
            except OSError:
                pass
            stdout_data, stderr_data = proc.communicate()
        finally:
            stop_monitor.set()
            monitor_thread.join(timeout=2)

        peak_memory_mb = peak_mb_holder[0]
        duration = time.monotonic() - start_time
        exit_code = proc.returncode if not timed_out else -9

        error_details = self.detect_render_errors(stdout_data, stderr_data)

        # Count rendered frames from "Saved:" lines in stdout
        frames_rendered = stdout_data.count("Saved:")

        success = exit_code == 0 and not timed_out

        if success:
            self._logger.info(
                "Blender run completed in %.1fs, frames=%d, peak_mem=%.1fMB",
                duration,
                frames_rendered,
                peak_memory_mb,
            )
        else:
            self._logger.error(
                "Blender run failed: exit_code=%d, timed_out=%s, duration=%.1fs",
                exit_code,
                timed_out,
                duration,
            )
            for err in error_details[:10]:
                self._logger.error("  Blender error: %s", err)

        return BlenderResult(
            success=success,
            exit_code=exit_code,
            stdout=stdout_data,
            stderr=stderr_data,
            duration_seconds=round(duration, 3),
            peak_memory_mb=round(peak_memory_mb, 1),
            frames_rendered=frames_rendered,
            error_details=error_details,
        )
