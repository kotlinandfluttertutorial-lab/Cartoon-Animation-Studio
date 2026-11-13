# Stage 10 character modelling

## Scope and files

Reviewed Stage 0–9 reports, the working character blends, the original generators `create_aarav.py` and `create_aanya.py`, and the existing `character_utils.py`, `character_movement.py`, `gesture_library.py`, `render_story_scene.py`, and facial scripts. Stage 9 measurements supported Workbench for these previews. The implementation plan is in `output/stage10_character_previews/implementation_plan.md`.

Added `blender/scripts/build_stage10_characters.py` and a small readiness guard in `facial_preview.py` so the Stage 4 facial alignment offsets are applied only once. The two variants and their previews are under `output/stage10_character_previews/final/`. The separate Blender files provide the rollback boundary. All 164 original asset hashes and the original final video hash matched.

## Design

- Aarav has a sculpted head profile, grouped swept hair locks, rounded shoulder caps, tapered sleeves and trousers, cuff trim, collar and buttons, thumb details and layered shoes.
- Aanya has a tapered face inside an open-front scarf shell. The shell wraps the crown and back, has a solidified opening edge, and tapers into a folded shoulder drape. The original panel names remain available in the asset. The garment uses a tapered torso, flared hem and coordinated shoes.
- Both faces use larger eyes, separate pupils and highlights, angled brows, rounded noses and the existing surface-fitted expression and speech shapes. No textures, simulations or high subdivision levels were added.

## Automated verification

Blender checked original bone names, hierarchy and rest matrices and existing action curves before and after modelling. Each character retains 20 bones and six actions. All twelve actions were sampled four times with at least three distinct mesh poses per action. The build checked the required face and limb meshes, original rigid parenting, usable materials, bone references, sampled shoulder and foot bounds, and solo preview framing. Weighted skinning, armature modifiers and weight groups are outside the original rigid-mesh rig contract. The separate saved files were reopened with the existing expression command, which rendered both happy expressions successfully.

The 21 requested and supplementary PNGs decoded at 640 × 360. Blender rendered a separate 36-frame walk, wave and dance sample at 12 fps. FFmpeg encoded and decoded the full clip. The existing suite passed 182 tests with one deprecation warning in a disposable copy.

## Performance

| Character | Source base faces | Evaluated visible faces | Original working blend load |
| --- | ---: | ---: | ---: |
| Aarav | 684 | 6,466 | 0.009 s |
| Aanya | 818 | 6,724 | 0.013 s |

The face counts include evaluated details and scarf thickness on the variants. The source counts describe raw geometry, so these values characterize added complexity rather than an identical evaluation benchmark. The first solo render took 1.806 s. Remaining solo renders took 0.062–0.113 s. The build and still previews completed in 5.97 s with a sampled peak Blender working set of 323 MiB. GPU memory was outside this measurement.

## Visual review and limitations

The assistant inspected the contact sheets, paired garden still and sampled motion poses. The rounded shapes and continuous scarf improve the silhouettes. The inherited wave angles can be shallow, and rigid elbows and wrists still show seams in some poses. The scarf follows the head, with some expected overlap around the collar. Exhaustive scarf collision testing and deforming skin are outside this prototype. The Stage 6 production path continues to load the original working blends.

The user explicitly approved Stage 10. Stage 11 uses these approved character variants.
