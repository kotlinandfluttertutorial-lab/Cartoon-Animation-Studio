# Stage 0 — Hardware Feasibility Audit
**Local 3D Cartoon Animation Studio**  
Date: 2026-11-10 | Blender 4.4.3 | Windows 10/11

---

## 1. System Inventory

| Component | Detail |
|---|---|
| CPU | Intel Core i7-8650U @ 1.90GHz (4 cores / 8 threads) |
| RAM | 32 GB |
| GPU | Intel UHD Graphics 620 (integrated, 1 GB shared VRAM) |
| GPU Driver | 31.0.101.2134 |
| OS | Windows 10/11 (build 10.0.26300) |
| Python | 3.11.9 (system) |
| FFmpeg | 9.0.2 (full build, via WinGet) |
| Ollama | Installed (Qwen3 4B) |
| Piper TTS | Installed |

---

## 2. Blender Installation

**Status: INSTALLED (portable)**

| Field | Value |
|---|---|
| Version | 4.4.3 |
| Build date | 2025-04-29 |
| Build hash | 802179c51ccc |
| Install type | Portable ZIP (no system install required) |
| Executable | `tools/blender-4.4.3-windows-x64/blender.exe` |
| Embedded Python | 3.11.11 |
| Source | mirror.blender.org |

Blender was downloaded and extracted to the project's `tools/` directory. It requires no installer, registry changes, or system permissions.

---

## 3. GPU, Driver & Render Engine Availability

### GPU Summary
- Intel UHD 620 is integrated graphics with shared VRAM (~1 GB).
- No NVIDIA/AMD discrete GPU → **no CUDA, no OptiX, no HIP**.
- OpenCL (Intel) is theoretically available but was not tested in headless mode.
- Vulkan support exists in the driver but was not tested.

### Render Engines Tested in Background Mode

| Engine | Headless | Result | Notes |
|---|---|---|---|
| **Workbench** | ✅ YES | **PASS** — 60 frames in 10.4s | Best choice for cartoon automation |
| **EEVEE Next** | ❌ NO | **FAIL** — requires GPU/display context | Blender 4.x EEVEE needs an active OpenGL context |
| **Cycles CPU** | ✅ YES | **PASS** — 60 frames in 1236s | Very slow; suitable only for stills |

---

## 4. Python Scripting Test

Blender's `--background --python` mode was verified working. All scene construction, render triggering, image saving, and JSON output via Python were successful.

```bash
blender.exe --background --factory-startup --python scripts/blender_scene_test.py
```

- Scene built entirely via `bpy` API (no .blend file required)
- Render triggered per-frame with `bpy.ops.render.render(write_still=False)`
- Frames saved with `bpy.data.images["Render Result"].save_render(path)`
- Full Python control loop confirmed working

---

## 5. Test Scene

The test scene contains:
- **Ground plane** — 10×10, green Principled BSDF material
- **Animated cube** — 1.5× scale, red material, rotates 360° over 60 frames
- **Animated sphere** — radius 0.8, blue/metallic material, bounces vertically
- **Camera** — positioned at (0, −8, 4), looking at scene center
- **Sun light** — energy 3.0, 45° angle

Scene parameters:
- Resolution: 640×360
- FPS: 12
- Duration: 5 seconds (60 frames)

---

## 6. Render Benchmarks

### Workbench Engine

| Metric | Value |
|---|---|
| Total render time | **10.37 seconds** |
| Average frame time | **0.172 s/frame** |
| Steady-state avg (frames 2–60) | ~0.13 s/frame |
| First-frame overhead | 4.08 s (GPU context init) |
| Minimum frame time | 0.086 s |
| Maximum frame time | 4.08 s (frame 1 only) |
| Frames completed | 60 / 60 ✅ |
| Output size | 13.17 MB (60 PNG frames) |
| Peak memory | ~22 MB |

**Projected rendering speeds (Workbench):**

| Resolution / FPS | 1 minute of animation | Notes |
|---|---|---|
| 640×360 @ 12 fps | ~2 min | Tested ✅ |
| 1280×720 @ 12 fps | ~8 min | Estimated (4× pixels) |
| 1280×720 @ 24 fps | ~16 min | Estimated |
| 1920×1080 @ 24 fps | ~60+ min | Not recommended |

### Cycles CPU Engine

| Metric | Value |
|---|---|
| Samples per frame | 32 (low-quality setting) |
| Total render time | **1,236 seconds (20.6 min)** |
| Average frame time | **20.6 s/frame** |
| Min frame time | 9.47 s |
| Max frame time | 39.76 s |
| Frames completed | 60 / 60 ✅ |
| Peak memory | ~29 MB |
| Notes | High variance due to thermal throttling |

Cycles CPU is **120× slower** than Workbench for this scene. Useful only for single high-quality stills.

### EEVEE Next Engine

| Metric | Value |
|---|---|
| Status | **FAILED** |
| Reason | Requires active OpenGL/GPU context in `--background` mode |
| Workaround | Mesa software renderer or virtual display (Xvfb/WSL2) — not pursued |

---

## 7. FFmpeg Test

```
Input:  60× PNG frames (640×360) from Workbench render
Output: stage0_test.mp4 (H.264, CRF 23, preset fast, yuv420p)
```

| Metric | Value |
|---|---|
| Input | 60 PNG frames @ 12 fps |
| Output file | `output/video/stage0_test.mp4` |
| Output size | **53 KB** |
| Duration | 5 seconds |
| Codec | libx264 (H.264) |
| Status | ✅ SUCCESS |

FFmpeg 9.0.2 successfully assembled Blender-rendered PNGs into a playable MP4.

---

## 8. Missing Dependencies

| Dependency | Status | Action Required |
|---|---|---|
| Blender | ✅ Present (portable 4.4.3) | None |
| Python 3.11 | ✅ Present | None |
| FFmpeg 9.0.2 | ✅ Present | None |
| Ollama / Qwen3 4B | ✅ Present | None |
| Piper TTS | ✅ Present | None |
| Mesa / LLVMPipe | ⚠️ Not installed | Optional: needed only if EEVEE headless is required |
| Virtual display (Xvfb) | ❌ Not applicable on Windows | Use WSL2 + Xvfb if EEVEE is mandatory |
| CUDA | ❌ Not present | Not applicable — no NVIDIA GPU |
| numpy, mathutils | ✅ Bundled in Blender | None |

No blocking missing dependencies for the Workbench-based pipeline.

---

## 9. Recommendation

### ✅ Primary: Blender Workbench

**Use Workbench for all automated cartoon animation rendering.**

- Fully headless-compatible (`--background` mode)
- Renders 640×360 at ~0.13 s/frame (steady state)
- 5-second animation completes in ~10 seconds
- Flat/solid shading with configurable outlines = natural cartoon look
- Low memory footprint (~22 MB peak for simple scenes)
- Python-controllable end-to-end

### ⚠️ Secondary: Cycles CPU

**Use only for single high-quality preview frames.**

- Works headless but very slow (~20s/frame at 32 samples)
- A 5-second animation would take ~20 minutes
- Not practical for production animation loops

### ❌ Avoid: EEVEE Next (headless)

**Do not use for automated rendering without a virtual display setup.**

- Requires OpenGL GPU context — fails in `--background` on this hardware
- Would require Mesa + LLVMPipe (software GL) or WSL2 + Xvfb to work
- Much higher complexity for minimal visual gain over Workbench

---

## 10. Overall Verdict

> **FEASIBLE.** This PC (i7-8650U, 32 GB RAM, Intel UHD 620) can produce simple 3D cartoon animations using Blender 4.4.3 in Workbench mode. At 640×360 / 12 FPS, a 1-minute cartoon renders in approximately 2 minutes. The pipeline — Python → Blender → FFmpeg → MP4 — is fully functional and automation-ready.

**Proceed to Stage 1 implementation using Blender Workbench engine.**

---

*Audit performed with Blender 4.4.3 portable, Python 3.11.9, FFmpeg 9.0.2 on Windows 10/11.*
