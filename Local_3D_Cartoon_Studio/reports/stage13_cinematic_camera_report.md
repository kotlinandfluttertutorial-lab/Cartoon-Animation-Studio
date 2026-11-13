# Stage 13 cinematic camera and lighting review

**Stage status** `BLOCKED` pending Stage 12 human approval. Independent camera and lighting studies are `VISUAL_REVIEW_PENDING`.

## Scope and compatibility

Stage 12 passed its full automated suite and pre-push check. Its recorded human approval is pending. This run opens the approved Stage 11 garden and appends the approved Stage 10 cast in Blender memory. Standalone studies use stationary cast poses. Follow, tracking and reveal test the camera path independently. Animated blocking, speaker and listener eyelines, transitions, and dialogue synchronization remain for the 20–30 second sequence after Stage 12 sign-off.

Added `blender/scripts/stage13_camera.py`, `blender/scripts/render_stage13_camera_studies.py`, `tests/test_stage13_camera.py`, and these reports and previews. All 168 protected files matched their original SHA-256 hashes, including the approved models, garden, source assets and Stage 8 video.

## Camera and lighting

The module defines ten camera presets and nine deterministic movement presets. Positions are based on the garden's performance lane. Smoothstep interpolation accepts custom end positions and targets. The over-the-shoulder revision turns Aarav away and shows Aanya's face. The extreme close-up intentionally crops the top of Aarav's hair.

Six Workbench treatments vary studio light, exposure, shadows, cavity and sky color. Stage 0 and Stage 9 both recommend Workbench for automated rendering. The reference images inform path framing, color and subject separation. Workbench provides studio shading and simplified shadows, with no physical area lighting, optical depth of field or volumetrics in these previews.

## Deliverables and verification

Review the camera and lighting contact sheet under `output/stage13_cinematic_previews/contact_sheets`. The nine silent two-second clips are under `studies/camera_movements`. Use `shoulder_revision` for the final over-the-shoulder still. Per-frame camera metadata, framing bounds and render times are in `studies/metadata/studies.json`.

The renderer checked projected bounds for selected head and limb landmarks on each applicable frame. FFprobe verified 640 × 360 at 12 fps and 24 frames per movement clip. All nine clips passed full decoding and PNG integrity checks. The assistant inspected the still contact sheet and revised shoulder shot. Full scene collision checks, audio continuity and animated shot transitions remain open. Repeated frames are intentional in the static camera study.

The targeted pytest run recorded 28 tests, 0 failures, 0 errors and 0 skips. It covered Stage 13 presets and movement, Stage 4.3 face geometry, the Stage 4.4 timeline, Stage 5 story and audio, and Stage 6 render assembly.

## Performance

The 216 movement frames rendered in 49.95 seconds, averaging 0.231 seconds per frame. The main process took 65.61 seconds and peaked at 332.29 MiB of sampled working-set memory. Scene and cast initialization took 0.083 seconds. Encoding took 2.43 seconds and the nine MP4s total 837,918 bytes. The shoulder revision ran separately. Stage 0 measured 0.172 seconds per frame on its smoke-test scene. Stage 12 measured about 0.290 seconds per frame for its animated garden previews. These workloads differ in scene content and pose evaluation.

## Human review

- [ ] Check establishing composition, intentional crops, and face readability.
- [ ] Play the movement studies and check for sudden changes, shake, or obstruction.
- [ ] Compare face colors, shadow strength, and grounding across the six looks.
- [ ] After Stage 12 sign-off, check moving character framing, hijab alignment, eyelines, shot transitions, audio sync, and sequence continuity on the assembled preview.

Human approval is pending.
