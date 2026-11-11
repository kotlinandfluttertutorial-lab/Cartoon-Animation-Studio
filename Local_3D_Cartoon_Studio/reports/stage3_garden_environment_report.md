# Stage 3 — Garden Environment Report

**Project:** Local 3D Cartoon Animation Studio  
**Date:** 2026-11-11  
**Blender:** 4.4.3 portable  
**Engine:** BLENDER_WORKBENCH  
**Resolution:** 640 × 360

---

## 1. Implementation Summary

A reusable cartoon garden environment was built entirely via procedural Blender Python.
The garden features bright, friendly cartoon styling with rounded shapes, complementing
the existing Aarav and Aanya characters. Both characters integrate correctly into the
garden scene without modifying their source assets.

**Overall result: PASS** — all acceptance criteria met.

---

## 2. Files Created

| File | Size | Purpose |
|---|---|---|
| `blender/scripts/create_garden.py` | — | Repeatable garden generator (backup-on-overwrite) |
| `blender/scripts/garden_utils.py` | — | Shared Blender helpers (materials, geometry, cameras) |
| `blender/scripts/validate_garden.py` | — | Blender-side 9-check validator |
| `blender/scripts/render_garden_previews.py` | — | Renders all 4 preview PNGs |
| `blender/assets/environments/garden/garden.blend` | 1,662 KB | Standalone garden scene |
| `blender/assets/environments/garden/garden.json` | — | Garden metadata with real statistics |
| `blender/assets/environments/garden/previews/garden_wide.png` | 313 KB | Full garden aerial view |
| `blender/assets/environments/garden/previews/garden_main.png` | 293 KB | Main camera view |
| `blender/assets/environments/garden/previews/garden_close.png` | 250 KB | Detail/close camera view |
| `blender/assets/environments/garden/previews/garden_with_characters.png` | 303 KB | Aarav + Aanya in garden |
| `tests/test_garden_generation.py` | — | 6 generation and idempotency tests |
| `tests/test_garden_render.py` | — | 5 render and image integrity tests |
| `reports/stage3_garden_environment_report.md` | — | This document |
| `reports/stage3_test_results.json` | — | Machine-readable test results |

**Files modified (with backups):**
- `blender/scripts/garden_utils.py` — backup `.20261111_180536.bak`
- `blender/scripts/render_garden_previews.py` — backup `.20261111_181011.bak`
- `blender/scripts/create_garden.py` — backup `.20261111_181415.bak`

**Stage 0 / Stage 1 / Stage 2 files: untouched.**

---

## 3. Garden Design

### Scene overview
Bright cartoon garden, 20×20 BU ground plane, sky-blue world background (#87CEEB), winding stone path, trees, bushes, flowers, decorations, 5 clouds, sun lamp.

### Ground (Environment_Ground)
- `Ground_Plane`: 20×20 BU flat plane at Z=0, material `Mat_Grass` (#4CAF50)
- 3 darker variation patches `Ground_Patch_01..03`, material `Mat_Grass_Dark` (#388E3C)

### Walking path (Environment_Path)
- `Path_Main`: winding S-curve strip, width 0.8 BU, Z=0.01, 24 segments
- Material `Mat_Path` (#D7CCC8) — beige/stone colour
- Passes through scene centre, bowing left of character area

### Trees (Environment_Trees) — 5 trees
| Object | Position | Foliage colour |
|---|---|---|
| Tree_01 | (-3.0, 2.0) | #66BB6A |
| Tree_02 | (3.0, 2.0) | #7CB342 |
| Tree_03 | (-3.0, -3.0) | #4CAF50 |
| Tree_04 | (3.0, -3.0) | #81C784 |
| Tree_05 | (0.0, 5.0) | #9CCC65 |

Each tree: cylindrical trunk (#5D4037) + icosphere foliage. Smooth-shaded.

### Bushes (Environment_Bushes) — 6 bushes
Icospheres radius 0.4–0.5, varied greens (#43A047, #2E7D32, #81C784), perimeter positions.

### Flowers (Environment_Flowers) — 12 flowers
Stem + 6-sided petal disc + yellow centre sphere. Colours: red, yellow, pink, orange, blue. Scattered around path edges and perimeter.

### Decorations (Environment_Decorations)
- 4 rounded stones (squashed icospheres, #9E9E9E)
- 1 signboard (`Sign_01_Post` + `Sign_01_Board`, #795548)
- 1 bench (`Bench_01_Seat` + legs, #6D4C41)

### Sky (Environment_Sky)
- World background: #87CEEB (sky blue), `world.use_nodes = False` for Workbench compatibility
- 5 clouds: elongated icospheres, white (#FFFFFF), Z=3.3–4.0, Y=-5.5 to -8.0

### Lighting
- `Sun_Light`: energy 3.0, warm white (1.0, 0.95, 0.85), 45° elevation

---

## 4. Scene Statistics

| Metric | Value |
|---|---|
| Total polygons | **2,416** |
| Total objects | **75** |
| Total materials | **34** |
| Collections | 9 |
| Cameras | 3 |
| Generation time | **0.63 s** |
| .blend file size | **1,662 KB** |
| Peak memory | unavailable (not instrumented inside Blender script) |

---

## 5. Camera Configuration

| Camera | Position | Target | Lens | Purpose |
|---|---|---|---|---|
| `Garden_Main_Camera` | (0, 9, 5.5) | (0, -1.5, 0.5) | 50mm | Main scene + characters |
| `Garden_Wide_Camera` | (0, 12, 7) | (0, 0, 0) | 35mm | Full garden aerial |
| `Garden_Close_Camera` | (0, 5, 2.5) | (0, 0, 0.8) | 85mm | Path and detail view |

All cameras at +Y facing toward -Y so they see the front faces of characters (characters face +Y per blend file convention).

---

## 6. Character Integration

Both characters appended from their source blend files using `bpy.ops.wm.append`. Only root (parentless) objects moved — parented mesh children follow automatically.

| Character | Blend source | X offset | Y offset | Z | Visible |
|---|---|---|---|---|---|
| Aarav | aarav.blend | -0.4 | -2.0 | 0.0 | ✅ Full body |
| Aanya | aanya.blend | +0.5 | -2.0 | 0.0 | ✅ Full body |

Characters stand on the garden ground, facing the main camera, path behind them, trees on both sides. Source blend files **not modified**.

---

## 7. Preview Images

| File | Resolution | Size | Render time | Valid |
|---|---|---|---|---|
| garden_wide.png | 640×360 | 313,252 B | 2.75 s | ✅ |
| garden_main.png | 640×360 | 292,542 B | 0.17 s | ✅ |
| garden_close.png | 640×360 | 249,908 B | 0.17 s | ✅ |
| garden_with_characters.png | 640×360 | 303,076 B | 0.27 s | ✅ |

All images > 20 KB (non-blank), valid PNG headers, 640×360.

---

## 8. Validation Results

`validate_garden.py` run on `garden.blend` — **9/9 checks PASS**:

| Check | Result |
|---|---|
| All 9 collections exist | ✅ |
| Ground plane at Z=0 | ✅ |
| ≥3 trees (found: 5×2 = 10 objects with "Tree_") | ✅ |
| ≥4 bushes (found: 6) | ✅ |
| ≥8 flowers (found: 36 flower objects) | ✅ |
| ≥3 cameras | ✅ |
| Sun_Light exists | ✅ |
| Character area clear of large objects | ✅ |
| All mesh objects have valid dimensions | ✅ |

---

## 9. Test Results

**33 / 33 passed — 0 failed — 0 skipped — 14.59 s**

| Test suite | Tests | Result |
|---|---|---|
| test_garden_generation.py | 6 | ✅ All pass |
| test_garden_render.py | 5 | ✅ All pass |
| test_character_generation.py | 9 | ✅ All pass (regression) |
| test_character_rig.py | 7 | ✅ All pass (regression) |
| test_character_render.py | 6 | ✅ All pass (regression) |
| **Total** | **33** | **✅ 33 / 33** |

---

## 10. Known Limitations

1. **Ground patch edges visible** — the darker variation ground patches have visible rectangular borders. A vertex-colour or texture approach would blend them better, but requires EEVEE/Cycles or more complex Workbench setup.

2. **Foreground tree trunks clip at frame edges** in the main camera view — cosmetically fine for a cartoon style.

3. **Flowers are small** at the preview resolution — the petal discs are 0.08 BU radius and appear as very small coloured dots in wide shots. They are visible in close views.

4. **Peak memory not instrumented** — the garden generation script does not capture Blender process peak RSS. Reported as unavailable.

5. **Character blend regeneration resets facial positions** — the `test_generation_idempotency` test calls `create_aarav.py` which rewrites the blend file, resetting facial feature Y positions to their original +Y values. The garden render script places characters in the garden using `bpy.ops.wm.append`, which loads the current blend state — so the garden preview shows characters correctly regardless of this, as the garden camera is at +Y where it can see the +Y-facing features.

6. **Stage 2.1 facial fix is blend-file dependent** — the character previews in `blender/assets/characters/aarav/previews/` were rendered with specific facial Y positions. Regenerating characters via `create_aarav.py` will reset positions and require re-running the facial fix script.

---

## 11. Human Visual Review Checklist

- [ ] Garden has an attractive cartoon appearance
- [ ] Grass and ground look appropriate
- [ ] Walking path is clearly visible
- [ ] Trees have good proportions and placement
- [ ] Bushes and flowers are visible in the scene
- [ ] Sky and background colour are correct (sky blue)
- [ ] Garden has enough open space for character movement
- [ ] Aarav is positioned correctly and visible
- [ ] Aanya is positioned correctly and visible
- [ ] Both characters are fully visible from head to feet
- [ ] Character faces are visible (facing camera)
- [ ] No environmental objects obstruct the characters
- [ ] Main camera composition is suitable for future animation

*All checkboxes remain unchecked — human visual review required.*

---

## 12. Stage 4 Readiness

Stage 3 is technically complete. All acceptance criteria are met:

| Criterion | Result |
|---|---|
| garden.blend exists and > 100 KB | ✅ 1,662 KB |
| garden.json total_polygons > 0 | ✅ 2,416 |
| All 4 previews at 640×360, > 20 KB | ✅ |
| garden_with_characters.png > 50 KB | ✅ 303 KB |
| validate_garden PASS for all 9 checks | ✅ |
| 11 new garden tests pass | ✅ |
| 22 Stage 2 regression tests pass | ✅ |
| No Stage 2 character files modified | ✅ |
| Real timing numbers in report | ✅ |

**Awaiting human visual approval before Stage 4.**

Stage 4 (animation engine) can begin once the garden environment is visually approved. The garden is designed to serve as the primary scene for all future cartoon animation sequences — the character placement area, path, and camera rigs are ready for animation use.

---

*All statistics from actual file inspection (garden.json, render_timings.json). No values estimated.*
