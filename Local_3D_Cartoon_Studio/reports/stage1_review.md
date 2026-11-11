# Stage 1 Review — Local 3D Cartoon Animation Studio

**Reviewer:** Automated review pass  
**Date:** 2025-01-10  
**Verdict:** APPROVED — no blockers found

---

## Checklist Evidence

### 1. File existence
All required files are present:
- `studio/schemas.py`, `studio/config_manager.py`, `studio/blender_runner.py`, `studio/ffmpeg_runner.py`, `studio/project_manager.py`, `studio/job_manager.py`, `studio/logger.py`, `studio/system_info.py`
- `app.py`, `README.md`, `requirements.txt`
- `config/settings.json`, `config/render_profiles.json`
- `blender/scripts/smoke_test.py`
- `tests/test_config.py`, `tests/test_blender_runner.py`, `tests/test_ffmpeg_runner.py`, `tests/test_project_manager.py`, `tests/test_job_manager.py`, `tests/test_integration.py`
- `reports/stage1_report.md`, `reports/stage1_test_results.json`

### 2. Pydantic v2 syntax
`schemas.py` imports and uses only `field_validator` and `model_validator` (Pydantic v2). The `AppSettings.validate_executable_path` validator uses `@field_validator` with `@classmethod`. No `@validator` decorators found anywhere in the codebase.

### 3. No shell=True
Searched all `.py` files. No occurrences of `shell=True`. All subprocess calls use list-form commands.

### 4. Windows paths
`settings.json` uses backslash Windows paths. Source files use `pathlib.Path` throughout. No hardcoded POSIX forward-slash paths found.

### 5. EXPERIMENTAL_720P disabled
`config/render_profiles.json` has `"enabled": false` for the `EXPERIMENTAL_720P` profile. `config_manager.get_profile()` raises `ValueError` for disabled profiles — confirmed by `test_config.py::TestGetProfileDisabled`.

### 6. Engine constraints
- `app.py` hardcodes `"engine": "BLENDER_WORKBENCH"` in the config dict passed to Blender.
- `blender/scripts/smoke_test.py` defaults to `"BLENDER_WORKBENCH"` and sets `scene.render.engine = engine`.
- EEVEE and Cycles appear only in Stage 0 artifacts (`scripts/blender_scene_test.py`, `scripts/blender_system_info.py`, `tests/test_stage0.py`) and in documentation/known-limitations comments in `app.py` and `README.md`. They are not used or reachable as defaults in any Stage 1 code path.

### 7. Backup logic
- `config_manager.py::save_settings()` — creates `config/backups/settings_<timestamp>.json` via `shutil.copy2` before overwriting.
- `project_manager.py::save_project()` — creates `projects/backups/<project_id>_<timestamp>.json` via `shutil.copy2` before overwriting an existing project file.
- Both guard with `if path.exists()` before creating the backup.

### 8. BlenderResult dataclass
All 8 required fields confirmed in `blender_runner.py`:
`success`, `exit_code`, `stdout`, `stderr`, `duration_seconds`, `peak_memory_mb`, `frames_rendered`, `error_details`.

### 9. FFmpegResult dataclass
`ffmpeg_runner.py` dataclass contains: `success`, `exit_code`, `output_path`, `duration_seconds`, `file_size_bytes`, `ffprobe_info`, `error_message`.

### 10. smoke_test.py
- Reads `BLENDER_CONFIG_PATH` env var; raises `RuntimeError` if missing/not found.
- Creates a cube, camera (at 5, -5, 3 pointed at origin), and sun light.
- Renders frames 1–3 via `bpy.ops.render.render(write_still=True)`.
- Writes `smoke_test_result.json` with `frames_rendered`, `avg_frame_time_s`, `total_time_s`, `engine`, `resolution`, `success`.

### 11. app.py behaviour
Runs in sequence: config load → system info → job creation → Blender smoke test → FFmpeg assembly → ffprobe validation → job completion → save both reports. Returns `sys.exit(main())` — exits 0 on full success, 1 on any step failure. Both `stage1_report.md` and `stage1_test_results.json` are written via `_save_reports()`.

### 12. Test coverage
All 6 test files exist and have been read:
- `test_config.py` — 7 unit tests covering load, invalid paths, profile retrieval, disabled profile, backup creation, Windows path round-trip. All mock `Path.exists` to avoid real filesystem dependency.
- `test_blender_runner.py` — 6 unit tests covering command construction, env var injection, non-zero exit, error detection, clean output, timeout/kill. All mock `subprocess.Popen` and `psutil.Process`.
- `test_ffmpeg_runner.py` — 6 unit tests covering command shape, audio stub warning, ffprobe validation (good, bad codec, zero duration). Mock `subprocess.Popen` and `subprocess.run`.
- `test_project_manager.py` — 5 unit tests covering create, save/load, list, backup-on-overwrite, delete confirmation guard. Use `tempfile.TemporaryDirectory`; no external process mocks needed.
- `test_job_manager.py` — 6 unit tests covering create, status transitions, failed status, interrupted-job recovery, list filter, persistence. Use `tempfile.TemporaryDirectory`.
- `test_integration.py` — 3 integration tests using `@unittest.skipUnless(_blender_available, ...)` / `@unittest.skipUnless(_blender_available and _ffmpeg_available, ...)` guards for graceful skip when executables are absent.

### 13. Stage 0 artifacts untouched
`p:\AI\Cartoon-Animation-Studio\reports\` contains only `stage0_hardware_a*` files.  
`p:\AI\Cartoon-Animation-Studio\scripts\` contains only `blender_system_info.py` and `blender_scene_test.py`.  
No Stage 1 writes occurred in those directories.

### 14. Real test results
`reports/stage1_test_results.json` contains actual measured data:
- Blender duration: 3.03 s, avg frame time: 0.588 s, total script time: 1.764 s
- Peak memory: 235.6 MB
- FFmpeg duration: 0.08 s, file size: 1775 bytes
- ffprobe: codec=h264, duration=0.25 s
- Total pipeline: 3.44 s

`reports/stage1_report.md` reflects the same values with no placeholder text.

### 15. requirements.txt
Contains exactly `pydantic>=2.0,<3.0`, `psutil>=5.9`, `pytest>=7.0`. No large or unnecessary dependencies.

---

## Findings

No blockers found.
