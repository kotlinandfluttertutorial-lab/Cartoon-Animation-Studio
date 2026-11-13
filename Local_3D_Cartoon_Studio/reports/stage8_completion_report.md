# Stage 8 first cartoon production

**Two Friends in the Magical Garden**

The six-scene story uses the existing Aarav, Aanya, and garden assets. The production adds establishing shots without characters, walking entrances, and a closing pullback. Dialogue, narration, background music, and sound cues were prepared locally with Piper and FFmpeg. The storyboard and each scene's actions were set explicitly for this sample.

A pilot render exposed a closing-shot obstruction and detached arms in the dance. The closing camera was adjusted, and Blender now evaluates the appended arm meshes before the dance setup reads their dimensions. The final renderer checks character head, torso, and foot framing, clear sightlines to those parts, upper-arm displacement, and ground contact on every character frame.

## Deliverables

- `output/first_cartoon/story.json`
- `output/first_cartoon/final_video.mp4`
- `output/first_cartoon/subtitles.srt`
- `output/first_cartoon/production_report.json`
- `output/first_cartoon/production_report.md`
- `reports/stage8_manual_review.md`

The render uses Blender Workbench. The user approved the Stage 8 export for visual and audio sign-off.

## Final verification

The 45-second export contains 1,080 frames at 1280 × 720 and 24 fps, with H.264 video, AAC audio, and eight selectable subtitle cues. The PNG sequences passed integrity checks and FFmpeg detected zero black frames. Sampled voice segments from all six scenes matched the source mix with no measured offset. The initial assembly accumulated AAC padding at scene boundaries. The final assembly joins the PCM scene mixes and encodes AAC once.

The resume check retained five intact frames and rendered the remaining 1,075. All 164 source asset hashes matched. The resumed render and initial assembly took 495.97 seconds. Peak memory could not be measured.

FFprobe reports that the video stream starts 23 ms after the audio stream. The measured source-to-export audio offsets above concern the audio track itself. Mouth timing remains approximate.

The final regression suite passed 182 tests with zero failures, errors, or skips. `check_before_push.py` exited 0 with 14 checks passed and two warnings for uncommitted changes and tracked backup files.
