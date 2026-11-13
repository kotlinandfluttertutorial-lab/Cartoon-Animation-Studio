# Stage 9 rendering engine and visual quality audit

## Current project

The Stage 0–8 pipeline builds reusable character and garden assets, uses rigid armature-parented meshes and sampled actions, plans and voices stories locally, and renders scenes with Workbench. FFmpeg composes numbered PNGs with a single AAC encode and subtitles. The Streamlit interface runs these commands as local jobs. The baseline was the Stage 8 cartoon and the separate visual-upgrade cut. This audit used a disposable scene and made no production code or asset edits.

The inspection covered the Stage 0 hardware audit and the project README and stage reports through Stage 8. Implementation paths included `create_aarav.py`, `create_aanya.py`, `character_utils.py`, `create_animations.py`, `character_movement.py`, `gesture_library.py`, `facial_preview.py`, `apply_lipsync.py`, `create_garden.py`, `garden_utils.py`, `garden_art_direction.py`, `render_stage44_preview.py`, `render_story_scene.py`, `config/render_profiles.json`, `studio/story_audio.py`, `studio/story_render.py`, and `studio_ui.py`.

## Engine comparison

[Matched comparison sheet](../output/stage9_visual_audit/engine_comparison.png). The comparison uses the same two characters, fixed orthographic camera, garden, tree and flower layers, path, bird and scene lights. The first image in every run samples frame 9. Eevee used 16 render samples. Cycles used 12 CPU samples and denoising. Workbench retained the existing art-direction setup with material colors, studio shading, cavity and softened shadows. Node-engine materials were initialized from the diffuse palette with shared roughness.

| Engine | Resolution | FPS | Frames | Mean render + save | Total process | Peak RSS | First PNG |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Workbench background | 640 × 360 | 12 | 12 | 0.362 s | 5.266 s | 313 MiB | 255,483 B |
| Workbench background | 640 × 360 | 24 | 24 | 0.294 s | 8.026 s | 313 MiB | 255,483 B |
| Workbench background | 1280 × 720 | 24 | 24 | 0.493 s | 12.880 s | 395 MiB | 914,592 B |
| Eevee background | 640 × 360 | 24 | 1 | 25.488 s | 26.588 s | 1170 MiB | 257,253 B |
| Eevee display | 640 × 360 | 24 | 3 | 9.197 s | 39.486 s | 1497 MiB | 257,253 B |
| Eevee display | 1280 × 720 | 24 | 3 | 10.872 s | 47.538 s | 1413 MiB | 930,675 B |
| Cycles CPU | 640 × 360 | 24 | 1 | 10.172 s | 11.793 s | 440 MiB | 276,933 B |
| Cycles CPU | 1280 × 720 | 24 | 1 | 16.448 s | 17.300 s | 958 MiB | 969,981 B |

The 12 and 24 fps Workbench runs each cover one second of bird animation. Frame timings include PNG writes and the first frame. Process totals include startup and exit. Peak RSS is sampled process working-set memory in MiB and excludes GPU memory. Some processes overlapped, so these are observed timings rather than isolated hardware limits.

- **Workbench** completed all 60 requested frames. It preserves the muted palette and clean edges. Shadows and cavity give useful shape, while studio lighting leaves faces flatter than a custom light rig. Disabling outlines in the prior visual-upgrade treatment keeps softened clothing edges clean.
- **Eevee Next** completed a background still and three consecutive renders at each resolution in a display-backed Blender process. The display reported Intel UHD Graphics 620 and OpenGL 4.6, driver build 31.0.101.2134. The 360p frame took 24.634 s cold and 1.449–1.509 s warm. The 720p frame took 25.850 s cold and 2.846–3.921 s warm. It showed stronger shadow separation, and the existing sun washed out the path and bright foliage. This run did not reproduce the Stage 0 background failure.
- **Cycles CPU** completed one still at each resolution. Indirect light and shading change the contact regions, but the existing sun still washes out bright colors and a foreground area reads nearly black. Reserve it for occasional stills on this configuration.

Keep Workbench for automated previews and production. Eevee is a viable option for lighting tests on this machine. Qualify a longer 720p sequence and retune materials and lights before promoting it to a production profile.

## Visual assessment

**Characters.** Oversized round heads read clearly, and eye glints improved the upgraded cut. Uniform spherical heads, peg necks, small brows and small projecting noses still limit facial identity. Mouth silhouettes read for open speech in close crops and become subtle in full-body shots. Aarav's hair reads as a separate cap. Aanya's hijab retains its recognizable silhouette but cap and side pieces have visible joins and little fabric drape. The torso and skirt have boxlike mass, and cylindrical limbs, mitten hands and block shoes make joints apparent. Rounded corners and coordinated palettes help. The remaining issue is continuity across pieces, particularly at shoulders, wrists, hips and footwear.

**Garden.** The ground plane and curved path establish the layout, but the flat horizon, broad grass patches and repeated spherical trees flatten the original. Existing benches and signs contribute little from the production framing. The upgraded flowers, hills and canopy lobes add depth. Clusters remain sparse and low against the large lawn. Low-poly birds read in silhouette, though wing shapes and positions repeat. Preserve a clear performance area, with differentiated plants and props layered outside the action.

**Animation and camera.** Sampled frames from both videos show visible walking entrances, waves and an alternating arm dance. The walk uses separate leg cycles and root travel, so sustained foot locking needs a dedicated playback check. Wave and pointing clips use short keyed arm changes, and their readability falls as the action settles in wide shots. Pointing and nodding also exist as isolated gesture previews. Small head turns and blink support exist in preview helpers, while the story renderer does not schedule idle blinks across every shot. The dance mostly swings rigid arms and keeps the feet planted. Add anticipation, torso counter-motion and responsive head looks. Character eyelines and reactions are weak because both performers are often posed toward the camera. Scene edits reset action state; a planned hold or matched pose would make the cuts feel connected. These findings use sampled poses and source inspection. They do not establish continuous-playback motion quality.

## Ranked recommendations

| Priority | Current problem | Proposed change and affected files | Expected result | Cost and complexity |
| --- | --- | --- | --- | --- |
| 1. Character modeling | Separate cylinders and boxes make silhouettes stiff. | Prototype tapered, rounded torso and overlapping joint shells on duplicate rigs. `create_aarav.py, create_aanya.py, character_utils.py` | More unified silhouettes and less visible joint separation. | Low with bounded topology. Medium |
| 2. Facial expressions | Small eye and brow changes are hard to read in wide shots. | Add editable eyelid and brow shapes, pupil aim and clearer smile and speech silhouettes. `facial_preview.py, expression_library.py, mouth_shapes.py` | Clearer reactions and dialogue poses. | Low for sparse shape keys. Medium |
| 3. Clothing, hair and hijab | Beveled blocks still read as separate pieces. | Model continuous scarf drape, broad hair locks, hems and cuffs using a few static meshes. `create_aarav.py, create_aanya.py, garden_art_direction.py` | Stronger character identity and fewer hard seams. | Low with static geometry. Medium |
| 4. Environment | Flat grass and repetitive canopy forms make the garden sparse. | Use grouped foliage silhouettes, layered hedges, flower clusters, path borders and distant trees. `garden_utils.py, create_garden.py` | Greater depth and a clearer walking lane. | Low to medium with instanced or batched meshes. Medium |
| 5. Character animation | Walking translation and leg cycles can slide. Waves and pointing settle quickly, and the dance relies on arm swings. | Add planted-foot tests and root-motion matching, sustained gesture poses, torso weight shifts, head reactions and idle blinks. `character_movement.py, gesture_library.py, render_stage44_preview.py, render_story_scene.py` | More readable, grounded motion and interaction. | Low render cost, higher authoring cost. High |
| 6. Lighting and shadows | Workbench compresses depth. The current sun clips pale colors in Eevee. | Keep a soft Workbench preset and prototype a lower-energy Eevee key with broad fill and contact shadows. `garden_utils.py, render_story_scene.py` | Better facial readability and grounding. | Workbench low. Eevee higher as measured. Medium |
| 7. Camera composition | Dialogue repeatedly uses frontal full-body shots. | Plan a wide establishing shot, alternating medium reactions, and a stronger closing pullback with eyeline continuity. `render_story_scene.py, story_planner.py` | Directs attention to faces and improves pacing. | Low unless using expensive effects. Medium |
| 8. Rendering quality | Engine changes reveal material mismatches and shadow artifacts. | Gate an optional Eevee profile on a longer repeated render and compare against Workbench. `config/render_profiles.json, studio/story_render.py` | Lighting options with a verified fallback. | Higher memory and render time for Eevee. Medium |
| 9. Final presentation | The export has abrupt pose changes at cuts and limited voice contrast. | Review a short edited animatic with reaction holds, subtitle legibility and balanced audio before a new full render. `stage6_render.py, studio/story_render.py, studio/story_audio.py` | Clearer storytelling and better rhythm. | Low for editorial changes. Medium |

## Validation and reproduction

The existing test suite passed **182 tests** with one existing deprecation warning, using a disposable copy with generator destinations redirected. Run the suite from the studio directory with `python -m pytest -q tests`. All comparison PNGs decoded at their expected sizes. FFmpeg encoded and fully decoded three Workbench clips. FFprobe confirmed each was one second at the requested rate and frame count. Exact Blender invocations, wall times, memory samples and exit status are in the per-run `*.process.json` files. The local FFmpeg commands used `-framerate FPS -i TAG_%02d.png -c:v libx264 -pix_fmt yuv420p TAG.mp4` and `-xerror -i TAG.mp4 -f null -`.

Build the comparison scene with `blender -b garden.blend --python audit_scene.py -- build`. For a background run, use `blender -b comparison.blend -t 6 --python-exit-code 1 --python audit_scene.py -- ENGINE WIDTH FPS COUNT TAG`. For a display-backed run, open the same scene with the same script and arguments in a new Blender process without `-b`. The script schedules rendering after window initialization and quits afterward. The GUI runs were display-backed automation. Manual Render Image and prolonged interactive editing were outside the measured test.

## Stage 10 proposal

1. Duplicate the two working character blends and map the existing names, origins and rest transforms before editing.
2. Prototype one silhouette for each character with connected-looking shoulders, tapered limbs and rounded shoes. Model a continuous-looking scarf and hair silhouette. Keep the palette and identity.
3. Add a small facial pose set and compare neutral, smile, surprised and speech poses under Workbench first.
4. Verify rest geometry, attachment during walk, wave and dance, mouth fit and preview cost. Present front and three-quarter comparisons and a short motion sample for review.

Main risks are changing pivot positions, clothing clipping through limbs, facial geometry no longer matching the head, and shader differences between engines. Use versioned working copies and compare the existing render path before promoting the models. No Stage 10 modelling was performed.
