# Stage 4.3 render fix report

**Human visual approval: PENDING.** The assistant inspected the six final Blender renders at their native 640 x 360 resolution.

## Reproduction and root causes

The six original PNGs were reproduced using Blender 4.4.3, the Stage 4.3 expression script from commit `32e7cd1`, the original one-off viseme preview script, and the existing Stage 4 working blends. [Before and after comparison](stage4_3_render_fix_comparison.png)

- `Aarav_Mouth` and `Aanya_Mouth` are eight-vertex boxes. The armatures have unit scale, the facial meshes use object parenting with identity parent-inverse matrices, and the local mouth origins lie below the nose. Authored mouth scale was (0.065, 0.015, 0.018), giving world dimensions of 0.130 x 0.030 x 0.036 Blender units. Assigning OPEN as an absolute scale made the boxes 2.6 x 2.0 x 2.8 units. Their pink materials filled or obstructed the view from the camera 4.5 units away.
- The original camera targeted Z = 0.875 from +Y for both characters. Aanya's nose and eyes sit on -Y. Stage 4.2.3 measures armature-relative rest offsets before posing and rotates the head around the neck pivot during nods. Its solo cameras follow the assets' native facing directions. Stage 4.3 now follows that convention without rotating the rigs.
- Aanya's rear hijab panel sat on the facial side and the cap extended toward her brows. Her iris and sclera surfaces met at the same depth. Aarav's mouth box was partly buried in the face, and the rectangle above his head was the authored cube geometry of `Aarav_Hair_Top`.

## Implementation and files

- `blender/scripts/facial_preview.py` shares the front-facing orthographic camera, Workbench setup, and ray-cast mouth fitting. Viseme factors multiply the current authored scale. A temporary surface silhouette gives each pose a readable shape, with the authored mesh and transforms restored after rendering.
- `blender/scripts/apply_lipsync.py` uses the shared path for each speech frame and scales eye whites and irises together during blinks. `blender/scripts/apply_expression.py` uses the expression library and the same mouth fitting.
- The preview scene moves Aanya's rear scarf panel behind the head, adjusts the cap and facial depths, and bevels Aarav's crown and fringe. Head, neck, torso, and armature transforms stay at their authored positions. These adjustments are in memory and use no new dependencies.
- `tests/test_stage4_3_render_geometry.py` and `tests/blender_stage43_probe.py` add Blender regression coverage for both characters. The six preview PNGs and this report's comparison sheet were regenerated.

## Final preview inspection

All six renders show the full character facing forward, with visible eyes, brows, nose, and mouth. The head and neck are attached, the sightline is clear, and Aanya's cap and panels stay in place.

| Preview | Reproduced defect | Final assistant inspection |
| --- | --- | --- |
| [aanya_speaking_1.png](../../output/stage4_3/previews/aanya_speaking_1.png) | Pink mouth box filled most of the frame | Pass. Open oval sits below the nose. |
| [aanya_speaking_2.png](../../output/stage4_3/previews/aanya_speaking_2.png) | Pink panel covered the face from the rear camera | Pass. The small closed MBP line contrasts with OPEN. |
| [aanya_surprised.png](../../output/stage4_3/previews/aanya_surprised.png) | Rear view obscured the expression | Pass. Raised brows, wide eyes, and a round open mouth read as surprise. |
| [aarav_happy.png](../../output/stage4_3/previews/aarav_happy.png) | A rectangular crown sat above a faint mouth | Pass. The crown and fringe are rounded and the smile curves upward. |
| [aarav_speaking_1.png](../../output/stage4_3/previews/aarav_speaking_1.png) | Oversized mouth filled the frame | Pass. The open oval and full character are visible. |
| [aarav_speaking_2.png](../../output/stage4_3/previews/aarav_speaking_2.png) | Oversized mouth covered the upper body | Pass. The wide, shallow EI silhouette differs from OPEN. |

## Lip-sync validation

The Blender tests exercise OPEN to EI on Aarav and OPEN to MBP on Aanya, followed by REST and a repeated OPEN. They compare world-space vertex coordinates for repeatability, verify that the temporary mouth follows the head surface, and check that speech leaves all other character transforms intact. They exercise each expression with and without a speech pose, then verify restoration of the original mouth mesh and world transforms. The actual rendered speaking PNGs confirm that the two poses on each character are visibly distinct.

## Automated tests and asset integrity

| Suite | Passed |
| --- | ---: |
| Stage 4.3, including both new Blender geometry tests | 36 |
| Stage 4.2.2 transform hierarchy and Stage 4.2.3 orientation regressions | 16 |
| Stage 4.2.1 reliability | 12 |
| Stage 4.2 movement | 20 |
| Stage 4.1 animations | 13 |
| Blender runner, character rig, and integration | 16 |
| Full pytest suite | 162 |

`python check_before_push.py` exited 0 with 14 checks passed, 0 failures, 2 warnings, and 0 skips. The warnings concerned local changes and tracked backup files. The full suite ran on Windows with portable Blender 4.4.3.

The first regression run exposed two legacy generators with absolute default output paths. It rewrote the local Aarav and garden generation outputs despite being launched from a disposable copy. The affected files were restored from the pre-run copies and generator backups. The final run set the generators' existing output overrides to the disposable copy. SHA-256 hashes matched for all 164 workspace asset files before and after that run. No character or garden asset is part of the render fix.

## Remaining limitations

The renderer uses stylized viseme silhouettes and solo assets. The still-image and geometry checks cover pose readability, deterministic geometry, and restoration. Continuous playback and audio alignment are outside this validation. Human approval remains pending.

## Git

- Branch codex/stage-4-3-render-fix
- Render fix commit 472569741fb45a3868cf47526d97166c520abf3c
- The validation report is recorded in a follow-up commit.
- PR URL pending local review.
