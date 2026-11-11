# Local 3D Cartoon Animation Studio — Stage 1

A modular Python foundation for automated 3D cartoon animation using Blender Workbench, FFmpeg, and Ollama (Qwen3).

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11.9 | Windows x64 |
| Blender | 4.4.3 portable | Background mode + Workbench engine |
| FFmpeg | 9.0.2 | Full build (includes ffprobe) |

---

## Installation

```powershell
# From the project root
pip install -r requirements.txt
```

Packages installed:
- `pydantic>=2.0,<3.0` — data validation (v2 syntax)
- `psutil>=5.9` — process and system monitoring
- `pytest>=7.0` — test runner

---

## Configuration

Edit `config/settings.json` to set paths before running:

```json
{
  "blender_executable": "...",
  "ffmpeg_executable": "...",
  "ffprobe_executable": "...",
  "output_dir": "...",
  "projects_dir": "...",
  "logs_dir": "..."
}
```

Render profiles are in `config/render_profiles.json`. Never edit them directly in production — always use a backup-creating method.

---

## Running the application

```powershell
python app.py
```

This performs a complete end-to-end smoke test:
1. Loads configuration
2. Collects system info (CPU, RAM, GPU, software versions)
3. Creates a job record
4. Runs Blender in background mode to render 3 PNG frames
5. Assembles the frames into `output/smoke_test.mp4` with FFmpeg
6. Validates the MP4 with ffprobe (checks h264 codec and duration)
7. Saves reports to `reports/`

Exits 0 on success, 1 on failure.

---

## Running tests

### Unit tests (no Blender or FFmpeg required)

```powershell
python -m pytest tests/test_config.py tests/test_blender_runner.py tests/test_ffmpeg_runner.py tests/test_project_manager.py tests/test_job_manager.py -v
```

### All tests including integration

```powershell
python -m pytest tests/ -v
```

### Integration tests only (requires real Blender and FFmpeg)

```powershell
python -m pytest tests/test_integration.py -v
```

Integration tests are automatically skipped if Blender is not found at the configured path.

---

## Project structure

```
Local_3D_Cartoon_Studio/
├── app.py                      # End-to-end entry point
├── requirements.txt
├── README.md
├── config/
│   ├── settings.json           # Executable paths, directories
│   ├── render_profiles.json    # PREVIEW / INITIAL_PRODUCTION / EXPERIMENTAL_720P
│   └── backups/                # Auto-created timestamped backups
├── studio/
│   ├── __init__.py
│   ├── schemas.py              # Pydantic v2 models
│   ├── logger.py               # Structured rotating-file logging
│   ├── config_manager.py       # Load, validate, back up configuration
│   ├── system_info.py          # CPU / RAM / GPU / version collection
│   ├── blender_runner.py       # Blender subprocess runner
│   ├── ffmpeg_runner.py        # FFmpeg + ffprobe runner
│   ├── project_manager.py      # Project CRUD with backup
│   └── job_manager.py          # Job tracking and recovery
├── blender/
│   └── scripts/
│       └── smoke_test.py       # Blender-embedded Python smoke test
├── projects/                   # Saved project JSON files
├── output/                     # Rendered frames and assembled video
├── logs/                       # Rotating log files (app / blender / ffmpeg / jobs)
├── reports/                    # stage1_report.md, stage1_test_results.json
└── tests/
    ├── test_config.py
    ├── test_blender_runner.py
    ├── test_ffmpeg_runner.py
    ├── test_project_manager.py
    ├── test_job_manager.py
    └── test_integration.py
```

---

## Render profiles

| Profile | Resolution | FPS | Engine | MP4 Output | Enabled |
|---------|-----------|-----|--------|-----------|---------|
| PREVIEW | 640×360 | 12 | BLENDER_WORKBENCH | No | ✅ |
| INITIAL_PRODUCTION | 640×360 | 12 | BLENDER_WORKBENCH | Yes | ✅ |
| EXPERIMENTAL_720P | 1280×720 | 12 | BLENDER_WORKBENCH | No | ❌ |

`EXPERIMENTAL_720P` is disabled until 720p performance is benchmarked on this hardware.

---

## Known limitations

- **EEVEE Next headless fails** on Intel UHD 620 in the tested configuration (confirmed Stage 0). Never set as default engine.
- **Cycles CPU is too slow** for regular animation (confirmed Stage 0). Never set as default engine.
- **BLENDER_WORKBENCH** is the confirmed working headless render engine.
- **Audio mixing** in `FFmpegRunner.frames_to_mp4()` is stubbed — the `audio_path` parameter exists but is not yet wired into the FFmpeg command.
- **EXPERIMENTAL_720P** must remain `enabled: false` until benchmarked.

---

## Stage 0 audit results (reference)

- Workbench: 60 frames in 10.37 s on Intel i7-8650U
- Eevee Next: failed headless
- Cycles CPU: works but impractical for animation
