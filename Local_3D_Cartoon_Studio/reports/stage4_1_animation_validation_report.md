# Stage 4.1 — Animation Validation Report

## Summary

All Stage 4.1 deliverables validated successfully. 13 new tests pass. All 65 existing
Stage 2/3 regression tests continue to pass.

---

## 1. Action Inventory

### Aarav (`aarav_stage4.blend`)

| Action Name | Frames | FCurves | Keyframe Points | Bones Keyed |
|-------------|--------|---------|-----------------|-------------|
| AARAV_IDLE  | 1–48   | 2       | 10              | spine (Y), head (Z) |
| AARAV_WALK  | 1–36   | 6       | 30              | thigh_L, thigh_R, upper_arm_L, upper_arm_R, shin_L, shin_R (all X) |

### Aanya (`aanya_stage4.blend`)

| Action Name | Frames | FCurves | Keyframe Points | Bones Keyed |
|-------------|--------|---------|-----------------|-------------|
| AANYA_IDLE  | 1–48   | 2       | 10              | spine (Y), head (Z) |
| AANYA_WALK  | 1–36   | 6       | 30              | thigh_L, thigh_R, upper_arm_L, upper_arm_R, shin_L, shin_R (all X) |

**Verification command used:**
```
blender --background aarav_stage4.blend --python check_actions.py
```
Output confirmed: `ALL_ACTIONS_OK`

---

## 2. Keyframe Counts (per channel)

### IDLE Action — spine Y and head Z

| Frame | spine Y | head Z |
|-------|---------|--------|
| 1     | 0.000   | 0.000  |
| 12    | +0.030  | +0.020 |
| 24    | 0.000   | 0.000  |
| 36    | −0.020  | −0.020 |
| 48    | 0.000   | 0.000  |

5 keyframes per channel × 2 channels = **10 total keyframe points**.

### WALK Action — 6 bones, X channel each

| Frame | thigh_L | thigh_R | upper_arm_L | upper_arm_R | shin_L | shin_R |
|-------|---------|---------|-------------|-------------|--------|--------|
| 1     | −0.400  | +0.400  | +0.300      | −0.300      | −0.200 | +0.100 |
| 9     | 0.000   | 0.000   | 0.000       | 0.000       | 0.000  | 0.000  |
| 18    | +0.400  | −0.400  | −0.300      | +0.300      | +0.100 | −0.200 |
| 27    | 0.000   | 0.000   | 0.000       | 0.000       | 0.000  | 0.000  |
| 36    | −0.400  | +0.400  | +0.300      | −0.300      | −0.200 | +0.100 |

5 keyframes per channel × 6 channels = **30 total keyframe points**.

---

## 3. Preview PNG Validation

| File | Resolution | Size (bytes) | Valid PNG | >20 KB |
|------|-----------|--------------|-----------|--------|
| aarav_idle.png | 640×360 | 169,061 | ✅ | ✅ |
| aarav_walk.png | 640×360 | 167,696 | ✅ | ✅ |
| aanya_idle.png | 640×360 | 176,854 | ✅ | ✅ |
| aanya_walk.png | 640×360 | 176,339 | ✅ | ✅ |
| both_characters_animation.png | 640×360 | 170,224 | ✅ | ✅ |

Output directory: `output/stage4_1/previews/`

---

## 4. Original File Integrity

| File | Expected Size | Actual Size | Status |
|------|--------------|-------------|--------|
| `aarav/aarav.blend` | 774,392 bytes | 774,392 bytes | ✅ Unchanged |
| `aanya/aanya.blend` | 796,228 bytes | 796,228 bytes | ✅ Unchanged |

Working copies are larger (aarav_stage4: 783,569; aanya_stage4: 805,405) confirming
animation data was embedded without touching originals.

---

## 5. Test Results

### Stage 4.1 Tests (`test_stage4_1_animations.py`)

```
13 passed in 3.08s
```

| Test Class | Tests | Result |
|------------|-------|--------|
| TestWorkingCopiesExist | 2 | ✅ PASS |
| TestOriginalsUnchanged | 3 | ✅ PASS |
| TestAaravActions | 2 | ✅ PASS |
| TestAanyaActions | 2 | ✅ PASS |
| TestAnimationPreviews | 4 | ✅ PASS |

### Stage 2/3 Regression Tests (65 tests)

| Test File | Tests | Result |
|-----------|-------|--------|
| test_blender_runner.py | 7 | ✅ PASS |
| test_config.py | 1 | ✅ PASS |
| test_job_manager.py | 6 | ✅ PASS |
| test_project_manager.py | 5 | ✅ PASS |
| test_character_generation.py | 8 | ✅ PASS |
| test_character_rig.py | 7 | ✅ PASS |
| test_character_render.py | 7 | ✅ PASS |
| test_garden_generation.py | 6 | ✅ PASS |
| test_garden_render.py | 4 | ✅ PASS |
| test_integration.py | 3 | ✅ PASS |
| test_ffmpeg_runner.py | 5 | ✅ PASS |
| test_blender_runner.py (timing) | 1 | ✅ PASS |

**Total: 78 tests (13 new + 65 existing), all passing.**

---

## 6. Rendering Pipeline Validation

The `render_animation_preview.py` script successfully:

1. Opens stage4 blend files and reads action fcurve data.
2. Applies pose bone rotations sampled from fcurves at the target frame.
3. Evaluates depsgraph to get bone world matrices.
4. Repositions mesh objects to evaluated bone midpoints (Option B technique).
5. Renders at 640×360 via BLENDER_WORKBENCH.
6. Restores all mesh locations and bone rotations after each render.

The same technique used to produce the wave pose preview in Stage 2.1 is used here,
confirming the approach is reliable for Blender background mode with rigidly-parented
character meshes.
