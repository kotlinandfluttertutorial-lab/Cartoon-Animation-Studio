# Stage 12 animation review

The supplied images guided the poses, gaze and expressions. The review clips use the approved Stage 10 Aarav and Aanya models and the approved Stage 11 garden. They retain the project’s Workbench look and original character designs.

## Animation

- The previous system samples six Euler-curve actions per character and moves rigid mesh parts using the evaluated bone matrices. Stage 12 reuses the bone hierarchy, native facing directions and action data. The new preview controller adds pose cues in Python and leaves the source blends and production entry points intact.
- Ten expression presets blend from neutral using mouth silhouette, brow lift and tilt, and eye openness. The mouth overlay is ray-fitted in native head space and follows the head pose. Gaze offsets and blink timing are independently controlled. A fixed seed reproduces the blink schedule, including occasional double blinks.
- Talking previews use both existing Piper WAVs and their Stage 5 viseme JSON, with matching audio and animation start offsets. Without a speech package, the renderer uses a manual sequence that exercises seven mouth states.
- The walk matches root travel to a two-link leg solution and keeps each shoe level during stance. Aarav and Aanya have different cadences. The preview set includes solo and paired walking.
- Wave and point ease in and out, with separate shoulder, elbow and wrist motion. Nods use the inherited action with adjusted timing. Head shake, idle, dance and gaze follow-through use lightweight pose controls. Paired cues stage a greeting and response, shared smiles, mutual gaze, a camera wave and a synchronized dance.

## Review files

The 640 × 360, 12 fps MP4s and PNG sequences are under `output/stage12_animation_previews/final`. Use the revised clips under `pointing` and the two head-shake clips under `gesture_refinement`. The contact sheet samples the action and expression studies. The speech review inputs are in `speech_source`.

From the repository root, supply a fresh output directory. The command accepts `--only` followed by individual clip names and `--seed` to reproduce or vary blink timing.

```powershell
& ./tools/blender-4.4.3-windows-x64/blender.exe -b -t 6 --python-exit-code 1 --python Local_3D_Cartoon_Studio/blender/scripts/render_stage12_animation.py -- <fresh-output-directory> --speech-package Local_3D_Cartoon_Studio/output/stage12_animation_previews/speech_source
```

## Limitations

The rigs have rigid joints and simplified hands, so pointing uses the hand silhouette. Small shoulder and elbow seams can still be visible. The scarf follows the head as a rigid piece. The checks measure its attachment and do not establish clearance against the collar or every limb. Running was optional and is omitted. Speech timing follows WAV activity and approximate text timing. Stage 12 remains an opt-in preview renderer with pose cues defined in Python. Saved Blender action baking, external shot authoring and integration into the story renderer remain open. The walking clips start and end mid-cycle. Gesture and expression cues use eased transitions within each clip.

For Stage 13, review a short multi-shot edit for eyelines, transition timing and dialogue coverage before a full production render.

Human approval is pending.

## Verification and performance

- 28 review clips and 1021 associated PNGs passed integrity or full-decode checks. The assistant inspected sampled PNGs for both solo performers and the paired shots. Both talking clips have AAC audio.
- The renderer checked the six inherited actions per character, pose bone references, finite keys, rigid parenting, framing, mouth ray hits, planted-foot drift and the relative transform of Aanya's scarf. The sampled peak drift was below 0.001 mm per frame. All 168 protected file hashes matched, including the source assets, approved blends and the Stage 8 MP4.
- The main 973-frame run took 479.16 s wall time. Scene and cast loading took 0.093 s. Frame evaluation and rendering took 183.188 s and 281.844 s respectively. Peak sampled Blender working set was 330.25 MiB. GPU memory and a matched legacy performance baseline were outside this measurement.
- The regression retry recorded 174 passed tests. The Streamlit dashboard test and pre-push result are pending.