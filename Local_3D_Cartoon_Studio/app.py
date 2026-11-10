"""
app.py — Stage 1 entry point for the Local 3D Cartoon Animation Studio.

Runs a full end-to-end smoke test:
  1. Load config
  2. Collect system info
  3. Create a job
  4. Run the Blender smoke test
  5. Assemble PNG frames into MP4 with FFmpeg
  6. Validate the MP4
  7. Save reports
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure the project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from studio.logger import configure_logging, get_logger
from studio.config_manager import ConfigManager
from studio.system_info import collect as collect_system_info
from studio.blender_runner import BlenderRunner
from studio.ffmpeg_runner import FFmpegRunner
from studio.job_manager import JobManager
from studio.schemas import JobStatus

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CONFIG_DIR = _PROJECT_ROOT / "config"
LOGS_DIR = _PROJECT_ROOT / "logs"
JOBS_DIR = _PROJECT_ROOT / "logs" / "jobs"
OUTPUT_DIR = _PROJECT_ROOT / "output"
REPORTS_DIR = _PROJECT_ROOT / "reports"
SMOKE_SCRIPT = _PROJECT_ROOT / "blender" / "scripts" / "smoke_test.py"
SMOKE_FRAMES_DIR = OUTPUT_DIR / "smoke_test"
SMOKE_MP4 = OUTPUT_DIR / "smoke_test.mp4"


def _ensure_dirs() -> None:
    for d in (LOGS_DIR, JOBS_DIR, OUTPUT_DIR, REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def main() -> int:
    _ensure_dirs()
    configure_logging(LOGS_DIR)
    log = get_logger("app")
    log.info("=" * 60)
    log.info("Stage 1 — Local 3D Cartoon Animation Studio")
    log.info("=" * 60)

    overall_start = time.monotonic()
    summary: dict = {
        "timestamp": datetime.utcnow().isoformat(),
        "stage": 1,
        "steps": {},
    }

    # ------------------------------------------------------------------
    # 1. Load configuration
    # ------------------------------------------------------------------
    log.info("Loading configuration from %s ...", CONFIG_DIR)
    cfg = ConfigManager(CONFIG_DIR)
    try:
        cfg.load()
    except Exception as exc:
        log.error("Configuration load failed: %s", exc)
        summary["steps"]["config"] = {"success": False, "error": str(exc)}
        _save_reports(summary, success=False)
        return 1

    settings = cfg.settings
    log.info("Config loaded. Active profile: %s", settings.active_render_profile)
    summary["steps"]["config"] = {"success": True, "profile": settings.active_render_profile}

    # ------------------------------------------------------------------
    # 2. Collect system info
    # ------------------------------------------------------------------
    log.info("Collecting system info ...")
    try:
        sys_info = collect_system_info(
            blender_exe=settings.blender_executable,
            ffmpeg_exe=settings.ffmpeg_executable,
        )
        log.info("CPU:     %s", sys_info.cpu)
        log.info("RAM:     %.1f GB", sys_info.ram_gb)
        log.info("GPU:     %s", sys_info.gpu)
        log.info("Blender: %s", sys_info.blender_version)
        log.info("FFmpeg:  %s", sys_info.ffmpeg_version)
        log.info("Python:  %s", sys_info.python_version)
        log.info("OS:      %s", sys_info.platform)
        summary["system_info"] = sys_info.model_dump()
    except Exception as exc:
        log.warning("System info collection partial failure: %s", exc)
        summary["system_info"] = {"error": str(exc)}

    # ------------------------------------------------------------------
    # 3. Create job
    # ------------------------------------------------------------------
    job_mgr = JobManager(JOBS_DIR)
    job = job_mgr.create_job(
        "smoke_test",
        metadata={
            "script": str(SMOKE_SCRIPT),
            "output_dir": str(OUTPUT_DIR),
            "engine": "BLENDER_WORKBENCH",
        },
    )
    log.info("Job created: %s", job.job_id)
    job_mgr.update_status(job.job_id, JobStatus.RUNNING)

    # ------------------------------------------------------------------
    # 4. Run Blender smoke test
    # ------------------------------------------------------------------
    log.info("Running Blender smoke test ...")
    blender_runner = BlenderRunner(
        blender_exe=settings.blender_executable,
        timeout=settings.process_timeout_seconds,
    )
    config_dict = {
        "output_dir": str(OUTPUT_DIR),
        "width": 640,
        "height": 360,
        "engine": "BLENDER_WORKBENCH",
    }

    blender_start = time.monotonic()
    blender_result = blender_runner.run(str(SMOKE_SCRIPT), config_dict)
    blender_duration = time.monotonic() - blender_start

    summary["steps"]["blender"] = {
        "success": blender_result.success,
        "exit_code": blender_result.exit_code,
        "duration_seconds": round(blender_duration, 2),
        "peak_memory_mb": blender_result.peak_memory_mb,
        "frames_rendered": blender_result.frames_rendered,
    }

    if not blender_result.success:
        log.error("Blender smoke test FAILED (exit %d)", blender_result.exit_code)
        log.error("stderr tail: %s", blender_result.stderr[-3000:])
        job_mgr.update_status(job.job_id, JobStatus.FAILED,
                               error_message=f"Blender exit {blender_result.exit_code}")
        _save_reports(summary, success=False)
        return 1

    # Count actual PNG frames
    png_files = sorted(SMOKE_FRAMES_DIR.glob("*.png"))
    log.info(
        "Blender completed in %.1fs — %d PNG frames at %s",
        blender_duration,
        len(png_files),
        SMOKE_FRAMES_DIR,
    )

    if len(png_files) < 3:
        msg = f"Expected >= 3 PNG frames, got {len(png_files)}"
        log.error(msg)
        job_mgr.update_status(job.job_id, JobStatus.FAILED, error_message=msg)
        summary["steps"]["blender"]["success"] = False
        summary["steps"]["blender"]["error"] = msg
        _save_reports(summary, success=False)
        return 1

    summary["steps"]["blender"]["png_files"] = len(png_files)

    # Also read the JSON result that the script writes
    smoke_result_path = OUTPUT_DIR / "smoke_test_result.json"
    if smoke_result_path.exists():
        with open(smoke_result_path, "r", encoding="utf-8") as f:
            smoke_result_data = json.load(f)
        summary["steps"]["blender"]["smoke_result"] = smoke_result_data
        log.info("avg_frame_time=%.3fs", smoke_result_data.get("avg_frame_time_s", 0))

    # ------------------------------------------------------------------
    # 5. FFmpeg assembly
    # ------------------------------------------------------------------
    log.info("Assembling frames into MP4 with FFmpeg ...")
    ffmpeg_runner = FFmpegRunner(
        ffmpeg_exe=settings.ffmpeg_executable,
        ffprobe_exe=settings.ffprobe_executable,
    )

    ffmpeg_start = time.monotonic()
    ff_result = ffmpeg_runner.frames_to_mp4(
        frames_dir=str(SMOKE_FRAMES_DIR),
        output_path=str(SMOKE_MP4),
        fps=12,
    )
    ffmpeg_duration = time.monotonic() - ffmpeg_start

    summary["steps"]["ffmpeg"] = {
        "success": ff_result.success,
        "exit_code": ff_result.exit_code,
        "duration_seconds": round(ffmpeg_duration, 2),
        "output_path": ff_result.output_path,
        "file_size_bytes": ff_result.file_size_bytes,
    }

    if not ff_result.success:
        log.error("FFmpeg failed: %s", ff_result.error_message)
        job_mgr.update_status(
            job.job_id, JobStatus.FAILED,
            error_message=f"FFmpeg failed: {ff_result.error_message}",
        )
        _save_reports(summary, success=False)
        return 1

    log.info(
        "FFmpeg completed in %.1fs — %s (%d bytes)",
        ffmpeg_duration,
        SMOKE_MP4,
        ff_result.file_size_bytes,
    )

    # ------------------------------------------------------------------
    # 6. Validate MP4
    # ------------------------------------------------------------------
    log.info("Validating MP4 with ffprobe ...")
    try:
        probe_info = ffmpeg_runner.validate_output(str(SMOKE_MP4))
        video_streams = [
            s for s in probe_info.get("streams", [])
            if s.get("codec_type") == "video"
        ]
        codec = video_streams[0].get("codec_name", "unknown") if video_streams else "none"
        duration_str = probe_info.get("format", {}).get("duration", "0")
        duration_val = float(duration_str)
        log.info("MP4 valid: codec=%s duration=%.2fs", codec, duration_val)
        summary["steps"]["validate"] = {
            "success": True,
            "codec": codec,
            "duration_seconds": round(duration_val, 2),
        }
    except ValueError as exc:
        log.error("MP4 validation failed: %s", exc)
        job_mgr.update_status(
            job.job_id, JobStatus.FAILED,
            error_message=f"Validation failed: {exc}",
        )
        summary["steps"]["validate"] = {"success": False, "error": str(exc)}
        _save_reports(summary, success=False)
        return 1

    # ------------------------------------------------------------------
    # 7. Finalise job
    # ------------------------------------------------------------------
    job_mgr.update_status(job.job_id, JobStatus.COMPLETED, progress=1.0)
    total_duration = time.monotonic() - overall_start
    summary["total_duration_seconds"] = round(total_duration, 2)
    summary["overall_success"] = True

    # ------------------------------------------------------------------
    # 8. Print summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STAGE 1 COMPLETE")
    print("=" * 60)
    print(f"  Total time       : {total_duration:.1f}s")
    print(f"  Blender render   : {blender_duration:.1f}s  ({len(png_files)} frames)")
    print(f"  FFmpeg assembly  : {ffmpeg_duration:.1f}s")
    print(f"  MP4              : {SMOKE_MP4}  ({ff_result.file_size_bytes} bytes)")
    print(f"  Peak memory      : {blender_result.peak_memory_mb:.1f} MB")
    print("=" * 60)

    _save_reports(summary, success=True)
    return 0


def _save_reports(summary: dict, success: bool) -> None:
    """Write stage1_report.md and stage1_test_results.json."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON
    results_path = REPORTS_DIR / "stage1_test_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    # Markdown
    blender_step = summary.get("steps", {}).get("blender", {})
    ffmpeg_step = summary.get("steps", {}).get("ffmpeg", {})
    validate_step = summary.get("steps", {}).get("validate", {})
    sys_info = summary.get("system_info", {})
    smoke = blender_step.get("smoke_result", {})

    status_icon = "✅" if success else "❌"
    report_lines = [
        "# Stage 1 Report — Local 3D Cartoon Animation Studio",
        "",
        f"**Generated:** {summary.get('timestamp', 'unknown')}  ",
        f"**Overall result:** {status_icon} {'PASS' if success else 'FAIL'}",
        "",
        "## System",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| CPU | {sys_info.get('cpu', 'n/a')} |",
        f"| RAM | {sys_info.get('ram_gb', 'n/a')} GB |",
        f"| GPU | {sys_info.get('gpu', 'n/a')} |",
        f"| Blender | {sys_info.get('blender_version', 'n/a')} |",
        f"| FFmpeg | {sys_info.get('ffmpeg_version', 'n/a')} |",
        f"| Python | {sys_info.get('python_version', 'n/a')} |",
        f"| OS | {sys_info.get('platform', 'n/a')} |",
        "",
        "## Blender Smoke Test",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Success | {blender_step.get('success', 'n/a')} |",
        f"| Exit code | {blender_step.get('exit_code', 'n/a')} |",
        f"| Duration | {blender_step.get('duration_seconds', 'n/a')} s |",
        f"| Frames rendered | {blender_step.get('png_files', blender_step.get('frames_rendered', 'n/a'))} |",
        f"| Avg frame time | {smoke.get('avg_frame_time_s', 'n/a')} s |",
        f"| Peak memory | {blender_step.get('peak_memory_mb', 'n/a')} MB |",
        f"| Resolution | {smoke.get('resolution', '640x360')} |",
        f"| Engine | BLENDER_WORKBENCH |",
        "",
        "## FFmpeg Assembly",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Success | {ffmpeg_step.get('success', 'n/a')} |",
        f"| Duration | {ffmpeg_step.get('duration_seconds', 'n/a')} s |",
        f"| Output | {ffmpeg_step.get('output_path', 'n/a')} |",
        f"| File size | {ffmpeg_step.get('file_size_bytes', 'n/a')} bytes |",
        "",
        "## MP4 Validation",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Success | {validate_step.get('success', 'n/a')} |",
        f"| Codec | {validate_step.get('codec', 'n/a')} |",
        f"| Duration | {validate_step.get('duration_seconds', 'n/a')} s |",
        "",
        "## Total Pipeline Duration",
        "",
        f"{summary.get('total_duration_seconds', 'n/a')} seconds",
        "",
        "## Known Limitations",
        "",
        "- EEVEE Next headless rendering fails on this hardware (confirmed Stage 0).",
        "- Cycles CPU render is too slow for regular animation use.",
        "- BLENDER_WORKBENCH is the confirmed working engine for headless automation.",
        "- EXPERIMENTAL_720P profile is disabled until benchmarked.",
        "- Audio mixing in FFmpegRunner is stubbed (not yet implemented).",
        "",
    ]

    report_path = REPORTS_DIR / "stage1_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\nReports saved to: {REPORTS_DIR}")
    print(f"  {results_path}")
    print(f"  {report_path}")


if __name__ == "__main__":
    sys.exit(main())
