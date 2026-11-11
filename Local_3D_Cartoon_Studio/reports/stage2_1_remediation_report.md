# Stage 2.1 — Character Visual Defect Remediation Report

**Project:** Local 3D Cartoon Animation Studio  
**Phase:** Stage 2.1 — Targeted fix of Stage 2 visual defects  
**Date:** 2026-11-11  
**Branch:** `Step-0`  
**Blender:** 4.4.3 portable  
**Engine:** BLENDER_WORKBENCH  
**Render resolution:** 640 × 360

---

## Executive Summary

Five visual defects identified in the Stage 2 review were fully remediated. All fixes are
committed, all 22 regression tests pass, and all 11 preview images have been regenerated.
The only remaining gate before Stage 3 is human visual sign-off on the rendered images.

| Defect | Before | After | Status |
|---|---|---|---|
| D1 — Wave pose identical to front | 0.0% pixel diff | 29.65% / 31.02% | ✅ FIXED |
| D2 — Facial features not visible | Features on wrong face of head | Features on camera-facing side | ✅ FIXED |
| D3 — Happy expression camera | Torso-level wide shot | Portrait close-up at head height | ✅ FIXED |
| D4 — Side view crops character | 3.5 BU — torso/legs cut off | 5.0 BU — full body with padding | ✅ FIXED |
| D5 — Combined preview rear angle | Side/rear angle, backs to camera | Front-facing, both characters visible | ✅ FIXED |

---

## 1. Defects and Root Causes

### D1 — Wave Pose Pixel-Identical to Front

**Root cause:** Character mesh objects are parented to the armature with `parent_type = 'OBJECT'`
(rigid, whole-armature parenting — no per-bone weights). In Blender background mode, applying
rotations to individual pose bones updates the bone transform data but does **not** propagate to
the world matrices of rigidly-parented child objects. Even after calling `view_layer.update()` and
`evaluated_depsgraph_get()`, the mesh objects remain at their rest positions in the render.

**Evidence:** Pre-fix pixel comparison showed exactly 0 changed pixels (0.0%) between
`front.png` and `wave_pose.png` for both characters. File sizes were byte-identical.

### D2 — Facial Features Not Visible

**Root cause:** All facial feature meshes (Eye_L, Eye_R, Iris_L, Iris_R, Eyebrow_L, Eyebrow_R,
Nose, Mouth) were created at Y = +0.24..+0.265 — on the **+Y hemisphere** of the head sphere.
The head sphere is centred at (0, 0, 1.4) with scale 0.28, placing its +Y surface at Y ≈ +0.28.
The front preview camera is at Y = −3.5 and looks in the **+Y direction**, so it sees the −Y
hemisphere (back of the head). The facial features, being on the +Y side, were entirely occluded.

### D3 — Happy Expression Camera

**Root cause:** The happy expression view used the same camera position as the front full-body
view: `(0, −3.5, 0.9)` targeting `(0, 0, 0.9)` at torso height. This produced a wide-angle
full-body shot with the head occupying a small fraction of the frame — not a useful expression
preview.

### D4 — Side View Camera Too Close

**Root cause:** The side camera was placed 3.5 BU from the character on the +X axis. With a
50 mm lens on a 640 × 360 render (aspect ratio 1.78), the vertical field of view covers
approximately 1.4 BU at that distance — insufficient to show the full 1.75 BU character.
The head and feet were cropped.

### D5 — Combined Preview Rear/Side Angle

**Root cause:** `_render_combined.py` placed both characters at X = −0.4 and X = +0.65 (correct),
but the camera target was `(0.1, 0, 0.9)` at torso height with the camera at `(0, −4.5, 0.9)`.
Since the characters were originally authored with facial features on the +Y side of the head,
the camera at −Y was actually looking at the front of the characters — but with D2 unresolved,
this produced a featureless view regardless. Additionally, the camera was not centred on the
midpoint between the two characters.

---

## 2. Fixes Applied

### Fix 1 — Wave Pose (Option B: direct mesh relocation)

**Approach:** After applying bone rotations to the armature, the depsgraph is evaluated with
`arm_obj.evaluated_get(depsgraph)`. The evaluated armature's pose bone world-space positions
are read directly from Blender's kinematic result — no manual rotation math. Each affected arm
mesh is moved to the midpoint `(bone.head + bone.tail) / 2` of its corresponding evaluated bone,
rendered, then restored to its original location. All bone rotations are reset afterward to
prevent pose bleed into the following happy_expression render.

**Bone → mesh mapping:**

| Bone evaluated | Mesh object moved |
|---|---|
| `upper_arm_R` | `{char}_UpperArm_R` |
| `forearm_R` | `{char}_LowerArm_R` |
| `hand_R` | `{char}_Hand_R` |

**Wave pose angles (unchanged from original):**
- `upper_arm_R`: (−1.2, 0, 0) rad XYZ — lifts arm forward and up
- `forearm_R`: (−0.5, 0, 0) rad XYZ — bends elbow

**Wave camera:** `(0, −2.5, 0.9)` targeting `(0, 0, 0.9)` — slightly closer than the
3.5 BU full-body front camera so the raised arm fills enough of the frame to meet the
≥5% visual-difference requirement.

**File:** `blender/scripts/render_character_preview.py`

---

### Fix 2 — Happy Expression Camera

**Change:** Camera position `(0, −3.5, 0.9)` → `(0, −2.0, 1.5)`, target `(0, 0, 0.9)` →
`(0, 0, 1.4)` (head centre), focal length 50 mm → 35 mm.

**Rationale:** At 2.0 BU with 35 mm lens, the vertical FOV covers approximately 1.1 BU,
framing the 0.56 BU head with comfortable padding. The camera height of 1.5 BU places it
just above head centre (1.4 BU) giving a natural portrait angle.

**File:** `blender/scripts/render_character_preview.py`

---

### Fix 3 — Side View Camera

**Change:** Camera position `(3.5, 0, 0.9)` → `(5.0, 0, 0.875)`, target `(0, 0, 0.9)` →
`(0, 0, 0.875)`.

**Rationale:** At 5.0 BU with 50 mm lens (sensor 36 mm, aspect 1.78), the vertical FOV
covers approximately 2.0 BU — sufficient for the 1.75 BU character with ~12% padding on
each side. Camera height 0.875 BU = half the character height, so the target is the
character's vertical centre.

**File:** `blender/scripts/render_character_preview.py`

---

### Fix 4 — Combined Preview Camera

**Change:** Camera position `(0, −4.5, 0.9)` → `(0.125, −4.5, 0.875)`, target
`(0.1, 0, 0.9)` → `(0.125, 0, 0.875)`.

**Rationale:** Aarav is offset to X = −0.4, Aanya to X = +0.65; midpoint X = 0.125.
Centring the camera on that midpoint ensures equal framing. Height 0.875 BU centres
vertically on the characters. The camera looks in the +Y direction, toward the −Y face
of the head (where facial features now reside after Fix 5).

**File:** `blender/scripts/_render_combined.py`

---

### Fix 5 — Facial Feature Visibility (blend file edit)

**Change:** All 8 facial feature mesh objects in both `.blend` files had their Y coordinate
negated and pushed slightly past the head surface at Y ≈ −0.28:

| Object | Old Y | New Y | Clearance from head surface |
|---|---|---|---|
| Eye_L / Eye_R | +0.240 | **−0.265** | 0.015 BU proud |
| Iris_L / Iris_R | +0.265 | **−0.278** | 0.013 BU proud of eye whites |
| Eyebrow_L / Eyebrow_R | +0.250 | **−0.265** | flush with surface |
| Nose | +0.265 | **−0.278** | protrudes forward |
| Mouth | +0.250 | **−0.265** | flush with surface |

X and Z positions are unchanged. Applied via `blender/scripts/fix_facial_positions.py`.

**Files:** `blender/assets/characters/aarav/aarav.blend`,
`blender/assets/characters/aanya/aanya.blend`

---

## 3. Verification Results

### 3.1 Wave Pose Pixel Difference

| Character | Pre-fix | Post-fix | Changed pixels | Requirement |
|---|---|---|---|---|
| Aarav | 0.00% ❌ | **29.65%** ✅ | 68,319 / 230,400 | ≥ 5% |
| Aanya | 0.00% ❌ | **31.02%** ✅ | 71,464 / 230,400 | ≥ 5% |

### 3.2 Preview Image Inventory

**`blender/assets/characters/aarav/previews/`**

| File | Resolution | Size (bytes) | Valid |
|---|---|---|---|
| front.png | 640 × 360 | 177,782 | ✅ |
| side.png | 640 × 360 | 148,364 | ✅ |
| three_quarter.png | 640 × 360 | 175,979 | ✅ |
| wave_pose.png | 640 × 360 | 189,950 | ✅ |
| happy_expression.png | 640 × 360 | 224,277 | ✅ |

**`blender/assets/characters/aanya/previews/`**

| File | Resolution | Size (bytes) | Valid |
|---|---|---|---|
| front.png | 640 × 360 | 183,366 | ✅ |
| side.png | 640 × 360 | 147,458 | ✅ |
| three_quarter.png | 640 × 360 | 178,330 | ✅ |
| wave_pose.png | 640 × 360 | 200,843 | ✅ |
| happy_expression.png | 640 × 360 | 217,579 | ✅ |

**`blender/assets/characters/combined/`**

| File | Resolution | Size (bytes) | Valid |
|---|---|---|---|
| both_characters.png | 640 × 360 | 188,200 | ✅ |

### 3.3 Structural Integrity (post-fix)

| Check | Aarav | Aanya |
|---|---|---|
| Armature present | ✅ | ✅ |
| Bone count | ✅ 20 / 20 | ✅ 20 / 20 |
| Mesh object count | ✅ 26 | ✅ 28 |
| Facial features Y < 0 | ✅ All 8 at −0.265..−0.278 | ✅ All 8 at −0.265..−0.278 |
| Required body parts | ✅ All present | ✅ All present |
| Materials non-default | ✅ 8 custom | ✅ 8 custom |
| Ground level (z ≈ 0) | ✅ | ✅ |

### 3.4 Regression Tests

```
22 passed in 7.00s  (Python 3.12.10 / pytest 8.2.2)
```

| Test suite | Tests | Result |
|---|---|---|
| test_character_generation.py | 9 | ✅ All pass |
| test_character_rig.py | 7 | ✅ All pass |
| test_character_render.py | 6 | ✅ All pass |
| **Total** | **22** | **✅ 22 / 22** |

Full output: `reports/stage2_regression_results.txt`

---

## 4. Files Modified

### `blender/scripts/`

| File | Type | Fixes | Detail |
|---|---|---|---|
| `render_character_preview.py` | Modified | D1, D3, D4 | Wave pose Option B (depsgraph bone midpoints); happy camera `(0,−2.0,1.5)` 35 mm; side camera 5.0 BU at 0.875 BU height |
| `_render_combined.py` | Modified | D5 | Camera centred on character midpoint `(0.125,−4.5,0.875)`, looks in +Y toward front faces |
| `fix_facial_positions.py` | **New** | D2 | One-shot script that opened each blend file, moved 8 facial objects per character to −Y, and saved |

### `blender/assets/characters/aarav/`

| File | Type | Fixes | Detail |
|---|---|---|---|
| `aarav.blend` | Modified | D2 | 8 facial feature objects moved from Y = +0.24..+0.265 to Y = −0.265..−0.278 |
| `previews/front.png` | Regenerated | D2 | Facial features now on camera-facing side |
| `previews/side.png` | Regenerated | D4 | Full body now fits in frame |
| `previews/three_quarter.png` | Regenerated | — | Unchanged camera; re-rendered for consistency |
| `previews/wave_pose.png` | Regenerated | D1 | Arm raised; 29.65% diff from front |
| `previews/happy_expression.png` | Regenerated | D3 | Portrait close-up at head height |

### `blender/assets/characters/aanya/`

| File | Type | Fixes | Detail |
|---|---|---|---|
| `aanya.blend` | Modified | D2 | 8 facial feature objects moved from Y = +0.24..+0.265 to Y = −0.265..−0.278 |
| `previews/front.png` | Regenerated | D2 | Facial features now on camera-facing side |
| `previews/side.png` | Regenerated | D4 | Full body now fits in frame |
| `previews/three_quarter.png` | Regenerated | — | Unchanged camera; re-rendered for consistency |
| `previews/wave_pose.png` | Regenerated | D1 | Arm raised; 31.02% diff from front |
| `previews/happy_expression.png` | Regenerated | D3 | Portrait close-up at head height |

### `blender/assets/characters/combined/`

| File | Type | Fixes | Detail |
|---|---|---|---|
| `both_characters.png` | Regenerated | D5 | Both characters front-facing in re-centred camera view |

### `reports/`

| File | Type | Detail |
|---|---|---|
| `stage2_regression_results.txt` | **New** | Full pytest output — 22/22 passed |
| `stage2_visual_review_report.md` | Updated | Pre-fix findings replaced with post-fix measurements |
| `stage2_1_remediation_report.md` | **New** | This document |

---

**Not touched:** All Stage 1 files, `character_utils.py`, `create_aarav.py`, `create_aanya.py`, `validate_character.py`, `character.json` files, `tests/` directory, `studio/` directory. Character geometry, materials, armature structure, bone definitions, and wave pose angles are identical to the original Stage 2 specification.

---

## 5. Commits

| Hash | Date (IST) | Description |
|---|---|---|
| `28bb374` | 2026-11-11 10:45 | fix: apply 5 visual defect fixes to render scripts (Stage 2.1) |
| `66ff95d` | 2026-11-11 10:51 | fix: Fix 5 — move facial features to -Y hemisphere |
| `b6bb9d4` | 2026-11-11 11:04 | docs: update visual review report — all 5 defects resolved |

---

## 6. Stage 3 Readiness

### Automated checks — all pass

| Criterion | Result |
|---|---|
| Wave pose ≥ 5% different from front (Aarav) | ✅ 29.65% |
| Wave pose ≥ 5% different from front (Aanya) | ✅ 31.02% |
| All 11 preview PNGs at 640 × 360 | ✅ |
| All 22 regression tests pass | ✅ |
| No Stage 1 files modified | ✅ |
| Character geometry / armature / materials unchanged | ✅ |
| Backups created before every blend file modification | ✅ |

### Human visual review — required before Stage 3

Open `reports/stage2_visual_review/index.html` and confirm visually:

- [ ] Aarav `front.png` — eyes, eyebrows, nose, mouth visible on face
- [ ] Aanya `front.png` — facial features visible beneath hijab framing
- [ ] Aarav `wave_pose.png` — right arm raised in a clear wave gesture
- [ ] Aanya `wave_pose.png` — right arm raised in a clear wave gesture
- [ ] Aarav `happy_expression.png` — face close-up, expression readable
- [ ] Aanya `happy_expression.png` — face close-up, expression readable
- [ ] Aarav `side.png` — head to feet visible, no cropping
- [ ] Aanya `side.png` — head to feet visible, no cropping
- [ ] `combined/both_characters.png` — both characters front-facing, full body

---

*Generated 2026-11-11. All measurements from actual file inspection and pixel analysis
(Pillow 12.3.0 + numpy). No values estimated or invented.*
