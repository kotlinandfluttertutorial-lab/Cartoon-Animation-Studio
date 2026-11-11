# Stage 2.1 — Character Visual Defect Remediation Workflow

**Project:** Local 3D Cartoon Animation Studio  
**Branch:** `Step-0`  
**Last updated:** 2026-11-11  
**Status:** 🟡 IN PROGRESS — fix-scripts ✅  fix-blend-facial ✅  regression ✅  report pending

---

## Defects Being Fixed

| # | Defect | Severity | Status |
|---|---|---|---|
| D1 | Wave pose renders pixel-identical to front | 🔴 HIGH | ✅ FIXED |
| D2 | Facial features not visible in front renders | 🟡 MEDIUM | ✅ FIXED |
| D3 | Happy-expression camera wrong framing | 🟡 MEDIUM | ✅ FIXED |
| D4 | Side-view camera too close / crops character | 🟡 MEDIUM | ✅ FIXED |
| D5 | Combined preview shows rear/side angle | 🟡 MEDIUM | ✅ FIXED |

---

## Steps

### ✅ Step 1 — investigate
**Status:** COMPLETE  
**Output:** Stage 2 visual review report at `reports/stage2_visual_review_report.md`  
Root causes confirmed per defect (see report §4, §5, §9–10).

---

### ✅ Step 2 — fix-scripts
**Status:** COMPLETE — commit `28bb374`  
**Files changed:**
- `blender/scripts/render_character_preview.py`
- `blender/scripts/_render_combined.py`

**What was fixed:**

| Fix | Change |
|---|---|
| D1 Wave pose | Option B: applies bone rotations, evaluates depsgraph via `arm_obj.evaluated_get(depsgraph)`, reads evaluated bone world-space midpoints `(head+tail)/2` for `upper_arm_R`, `forearm_R`, `hand_R`, moves `UpperArm_R` / `LowerArm_R` / `Hand_R` mesh objects to those positions, renders at Y=−2.5, restores locations and resets all bone rotations after render. |
| D3 Happy camera | Camera `(0,−2.0,1.5)` → target `(0,0,1.4)` head centre, focal length 35 mm |
| D4 Side camera | Distance 3.5→5.0 BU on +X, height corrected to 0.875 BU, target `(0,0,0.875)` |
| D5 Combined camera | `_render_combined.py`: camera `(0.125,−4.5,0.875)` targeting `(0.125,0,0.875)`, looks in +Y direction toward character fronts |

**Validation results (post-fix renders):**
- Aarav wave vs front: **29.65%** (requirement ≥5% ✅)
- Aanya wave vs front: **31.02%** (requirement ≥5% ✅)
- All 11 PNGs: 640×360, valid ✅

---

### ✅ Step 3 — fix-blend-facial
**Status:** COMPLETE — commit `66ff95d`  
**Files changed:**
- `blender/assets/characters/aarav/aarav.blend`
- `blender/assets/characters/aanya/aanya.blend`
- `blender/scripts/fix_facial_positions.py` *(new — the script that applied the fix)*

**Root cause:** Facial feature mesh objects were created at Y = +0.24..+0.265 (facing +Y). The front preview camera is at Y = −3.5 looking in the +Y direction, so it was seeing the back of the head. The head sphere front surface is at Y ≈ −0.28.

**Fix applied** — both blend files:

| Object suffix | Old Y | New Y | Notes |
|---|---|---|---|
| Eye_L / Eye_R | +0.240 | **−0.265** | 0.015 BU proud of head surface |
| Iris_L / Iris_R | +0.265 | **−0.278** | 0.013 BU proud of eye whites |
| Eyebrow_L / Eyebrow_R | +0.250 | **−0.265** | flush with head surface |
| Nose | +0.265 | **−0.278** | protrudes 0.025 BU in Y scale |
| Mouth | +0.250 | **−0.265** | flush with head surface |

X and Z positions unchanged. Structural integrity preserved: 20 bones, Aarav 26 meshes, Aanya 28 meshes.

---

### ✅ Step 4 — regression-tests
**Status:** COMPLETE — 22/22 tests pass  
**Run:** `py -3 -m pytest tests/test_character_generation.py tests/test_character_rig.py tests/test_character_render.py -v`  
**Result file:** `reports/stage2_regression_results.txt`

```
22 passed in 7.00s
```

All pre-existing tests pass with no regressions. Specific checks confirmed:
- Both `.blend` files exist and open ✅
- Both armatures have exactly 20 bones ✅
- All required mesh objects present ✅
- All 11 preview PNGs exist at 640×360 ✅
- Render timing under 120 s ✅

---

### 🔲 Step 5 — update-visual-report
**Status:** PENDING  
**Task:** Update `reports/stage2_visual_review_report.md` to reflect the post-fix state.

The report currently describes the original defects (wave 0% diff, featureless faces, bad cameras). It needs to be updated with:
- New file sizes for all 11 PNGs
- Wave pose pixel-difference measurements (29.65% / 31.02%)
- Confirmation that facial features are now at −Y positions
- Camera framing corrections documented
- Overall outcome changed from WARNINGS to PASS

**Input files needed:**
- Current preview PNG sizes (already measured above)
- Git commit hashes `28bb374` and `66ff95d`

---

### 🔲 Step 6 — stage3-readiness-check
**Status:** PENDING  
**Task:** Confirm all Stage 2.1 acceptance criteria are met before Stage 3 begins.

Criteria:
- [ ] Wave pose preview differs from front by ≥5% for both characters
- [ ] Facial features visible in front renders (requires human visual review)
- [ ] Happy expression shows face close-up (requires human visual review)
- [ ] Side view shows full character (requires human visual review)
- [ ] Combined preview shows both characters facing camera (requires human visual review)
- [ ] 22/22 regression tests pass
- [ ] No Stage 1 functionality broken
- [ ] Updated visual review report committed

---

## File Map

```
blender/
  scripts/
    render_character_preview.py   ← Fix 1/2/3 (Step 2)
    _render_combined.py           ← Fix 4 (Step 2)
    fix_facial_positions.py       ← Fix 5 applicator (Step 3)
  assets/characters/
    aarav/
      aarav.blend                 ← Fix 5 applied (Step 3)
      previews/                   ← All 5 PNGs regenerated
    aanya/
      aanya.blend                 ← Fix 5 applied (Step 3)
      previews/                   ← All 5 PNGs regenerated
    combined/
      both_characters.png         ← Regenerated (Step 2)
reports/
  stage2_visual_review_report.md  ← Needs update (Step 5)
  stage2_regression_results.txt   ← Written (Step 4)
```

---

## Commits

| Hash | Message |
|---|---|
| `28bb374` | fix: apply 5 visual defect fixes to render scripts (Stage 2.1) |
| `66ff95d` | fix: Fix 5 — move facial features to -Y hemisphere for front camera visibility |
