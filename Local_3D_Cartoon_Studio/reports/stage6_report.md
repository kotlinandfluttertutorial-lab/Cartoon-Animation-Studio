# Stage 6 render and composition

## Pipeline

`stage6_render.py` reads a Stage 5 package containing the story plan, frame timing, mouth shapes, and per-scene WAV mixes. It uses the existing garden and character working blends, applies story actions and expressions, and renders numbered PNGs with Blender Workbench. The default preview profile uses the configured 640 x 360 at 12 fps. The optional production profile uses 1280 x 720 at 24 fps.

Each output folder contains scene PNGs and segments under `scenes/`, copied mixes under `audio/`, `subtitles.srt`, `progress.json`, `final_video.mp4`, and `production_report.json`. FFmpeg encodes H.264 video and AAC audio, adds short scene audio fades, and embeds selectable subtitles. FFprobe checks stream presence, frame count, resolution, frame rate, and duration. The final file is published after a full decode check.

A render job fingerprints its inputs, relevant Blender scripts, and profile. Blender writes each PNG through a temporary file. Resume scans frame dimensions and PNG chunk checksums, then renders missing or invalid frames. The command rejects changes to prepared inputs during resume and protects a completed MP4 from overwrite.

## Commands

Run from the studio directory. Supply the folder created by the Stage 5 story command.

```powershell
python stage6_render.py <prepared-folder> <new-output-folder> --frame-budget 12
python stage6_render.py <prepared-folder> <same-output-folder> --resume
python stage6_render.py <prepared-folder> <new-720p-output-folder> --quality 720p
```

Omit `--frame-budget` for an uninterrupted render. The project uses the configured local Blender, FFmpeg, and FFprobe executables.

## Scope

The sample exercises two characters, story gestures, expressions, approximate lip-sync, and a bird in the existing garden. The 720p test uses two short shots to exercise scene assembly and subtitle offsets. A full 45-second production and the Streamlit interface remain later roadmap work.

## Verified results

| Run | Video | Result |
| --- | --- | --- |
| Garden Bird Spot | 10 seconds, 640 x 360, 12 fps, 120 frames | Paused after 12 frames. Resume reused 11 intact files and rendered 109 frames, including the deliberately damaged frame. The recovered frame matched its original pixels. |
| Two-scene 720p check | 4 seconds, 1280 x 720, 24 fps, 96 frames | Both scenes encoded and assembled successfully. The second subtitle begins at 2.000 seconds. |

Both MP4s passed full video and audio decoding and contained H.264 video, AAC audio, and selectable subtitles. The assistant inspected frames from both exports. The completed-file protection was exercised against the 10-second MP4. SHA-256 checks matched for all 164 source asset files.

The resumed preview took 44.75 seconds, excluding the initial 12 frames. The two-scene 720p run took 71.59 seconds. These timings were measured while both jobs were active and are specific to the sample.

The final full suite passed 174 tests. `check_before_push.py` exited 0 with 14 checks passed, 0 failures, 0 skips, and two warnings for local changes and tracked backup files. Generator output was redirected to a disposable checkout during testing.
