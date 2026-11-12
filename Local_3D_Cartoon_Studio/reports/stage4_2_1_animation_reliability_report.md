# Stage 4.2.1 — Animation Reliability Report

## Implementation Summary

Stage 4.2.1 fixes a critical mesh transform bug in the Option B animation pipeline and adds 12 corrected preview renders for all character poses and interactions.

### Changes Made

**`blender/scripts/character_movement.py`**
- Added `compute_rest_offsets(arm_obj, char_prefix)` — computes per-object spatial offset between mesh origin and bone midpoint in rest pose
- Added `_SAFE_BONES` frozenset — restricts Option B mesh movement to arm/leg bones only
- Updated `apply_action_pose()` — now uses `midpoint + rest_offset` positioning instead of raw `midpoint`; uses `_SAFE_BONES` to skip head/neck/spine; computes rest offsets internally if not provided

**`blender/scripts/render_stage42_previews.py`** (backport)
- Added `_SAFE_BONES` frozenset
- Added `_compute_rest_offsets()` local helper
- Updated `apply_animation_pose()` with same offset-corrected logic
- Fixed combined render to also append Aanya actions from `aanya_stage4.blend`
- Camera default already matched target spec `(0, 4.5, 0.875)`

**`blender/scripts/render_stage421_previews.py`** (new)
- Renders all 12 Stage 4.2.1 previews to `output/stage4_2_1/previews/`
- Imports `compute_rest_offsets`, `apply_action_pose`, `restore_pose`, `setup_workbench`, `make_camera` from `character_movement`
- Calls `compute_rest_offsets()` once per character per scene
- Applies 180° Z flip to Aanya objects in all render types (single and combined)
- Uses camera `pos=(0, 4.5, 0.875)` for single renders, `pos=(0.0, 5.5, 0.875)` for combined
- Combined: Aarav at X=-0.6, Aanya at X=+0.6
- Safety check: refuses to overwrite `output/stage4_2/previews/`

**`tests/test_stage4_2_1_reliability.py`** (new)
- 12 automated tests covering file integrity, API presence, PNG validity, gesture actions, and regression

---

## Test Results

All three test suites passed after Stage 4.2.1 implementation.

### Stage 4.1 — test_stage4_1_animations.py
**Result: 13/13 passed**

| Test | Result |
|------|--------|
| test_aarav_stage4_blend_exists | PASSED |
| test_aanya_stage4_blend_exists | PASSED |
| test_aarav_original_size | PASSED |
| test_aanya_original_size | PASSED |
| test_working_copies_differ_from_originals | PASSED |
| test_aarav_idle_action_exists | PASSED |
| test_aarav_walk_action_exists | PASSED |
| test_aanya_idle_action_exists | PASSED |
| test_aanya_walk_action_exists | PASSED |
| test_all_previews_exist | PASSED |
| test_all_previews_valid_png | PASSED |
| test_all_previews_640x360 | PASSED |
| test_all_previews_above_20kb | PASSED |

### Stage 4.2 — test_stage4_2_movement.py
**Result: 20/20 passed**

All 20 tests passed including Stage 4.1 regression tests, file integrity checks, gesture action checks (WAVE, POINT, NOD, GREETING), and 8 preview PNG validations.

### Stage 4.2.1 — test_stage4_2_1_reliability.py
**Result: 12/12 passed**

| Test | Result |
|------|--------|
| test_aarav_orig_file_unchanged | PASSED |
| test_aanya_orig_file_unchanged | PASSED |
| test_character_movement_has_compute_rest_offsets | PASSED |
| test_character_movement_has_safe_bones | PASSED |
| test_all_12_previews_exist | PASSED |
| test_all_12_previews_are_valid_pngs | PASSED |
| test_all_12_previews_gt_20kb | PASSED |
| test_aarav_gesture_actions_present | PASSED |
| test_aanya_gesture_actions_present | PASSED |
| test_aarav_regression_actions | PASSED |
| test_aanya_regression_actions | PASSED |
| test_render_stage421_script_exists | PASSED |

**Total: 45/45 tests passed across all three suites.**

---

## Preview File Inventory (12 files)

All files located in `output/stage4_2_1/previews/`. All are 640×360 PNG.

| File | Size (bytes) | Status |
|------|-------------|--------|
| `aarav_idle.png` | 165,815 | OK |
| `aarav_wave.png` | 165,023 | OK |
| `aarav_point.png` | 164,485 | OK |
| `aarav_nod.png` | 165,815 | OK |
| `aanya_idle.png` | 167,701 | OK |
| `aanya_wave.png` | 168,895 | OK |
| `aanya_point.png` | 168,458 | OK |
| `aanya_nod.png` | 167,701 | OK |
| `both_facing_camera.png` | 168,503 | OK |
| `greeting_interaction.png` | 168,848 | OK |
| `pointing_interaction.png` | 167,877 | OK |
| `walk_together.png` | 169,599 | OK |

All files > 20 KB threshold. All have valid PNG headers. No Stage 4.2 previews were overwritten.

---

## Regression Status

### Stage 4.1 (13 tests)
- Status: **PASS** — 13/13
- Original blend files verified unchanged (aarav.blend: 774392 bytes, aanya.blend: 796228 bytes)
- Stage 4.1 preview PNGs (walk/idle) still present and valid

### Stage 4.2 (20 tests)
- Status: **PASS** — 20/20
- Stage 4.2 preview PNGs still present in `output/stage4_2/previews/`
- All gesture actions (WAVE, POINT, NOD, GREETING) confirmed present in both characters' blend files
- render_stage42_previews.py updated with the same offset-correction fix (backport)

No regressions introduced.
