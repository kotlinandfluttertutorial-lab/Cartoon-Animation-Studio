# Stage 1 Report — Local 3D Cartoon Animation Studio

**Generated:** 2026-11-10T08:11:50.476156  
**Overall result:** ✅ PASS

## System

| Field | Value |
|-------|-------|
| CPU | Intel64 Family 6 Model 142 Stepping 10, GenuineIntel, 4 cores, 2.1 GHz |
| RAM | 31.88 GB |
| GPU | Unknown |
| Blender | Blender 4.4.3 |
| FFmpeg | ffmpeg version 9.0.2-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers |
| Python | 3.11.9 |
| OS | Windows-10-10.0.26300-SP0 |

## Blender Smoke Test

| Metric | Value |
|--------|-------|
| Success | True |
| Exit code | 0 |
| Duration | 3.03 s |
| Frames rendered | 3 |
| Avg frame time | 0.588 s |
| Peak memory | 235.6 MB |
| Resolution | 640x360 |
| Engine | BLENDER_WORKBENCH |

## FFmpeg Assembly

| Metric | Value |
|--------|-------|
| Success | True |
| Duration | 0.08 s |
| Output | P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\output\smoke_test.mp4 |
| File size | 1775 bytes |

## MP4 Validation

| Metric | Value |
|--------|-------|
| Success | True |
| Codec | h264 |
| Duration | 0.25 s |

## Total Pipeline Duration

3.44 seconds

## Known Limitations

- EEVEE Next headless rendering fails on this hardware (confirmed Stage 0).
- Cycles CPU render is too slow for regular animation use.
- BLENDER_WORKBENCH is the confirmed working engine for headless automation.
- EXPERIMENTAL_720P profile is disabled until benchmarked.
- Audio mixing in FFmpegRunner is stubbed (not yet implemented).
