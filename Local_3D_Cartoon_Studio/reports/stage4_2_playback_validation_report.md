# Stage 4.2 — Playback Validation Report

**Project:** Local 3D Cartoon Animation Studio  
**Stage:** 4.2 — Character Movement, Interaction & Gesture System  
**Date:** 2026-11-11  
**Python:** 3.11.9  
**pytest:** 8.3.5

---

## Stage 4.2 Test Results

**Total: 20 tests — 20 PASSED, 0 FAILED, 0 ERRORS, 0 SKIPPED**

| # | Test | Result |
|---|---|---|
| 1 | test_stage41_regression_aanya_idle | PASS |
| 2 | test_stage41_regression_aanya_walk | PASS |
| 3 | test_stage41_regression_aarav_idle | PASS |
| 4 | test_stage41_regression_aarav_walk | PASS |
| 5 | test_original_aanya_unchanged | PASS |
| 6 | test_original_aarav_unchanged | PASS |
| 7 | test_character_movement_script_exists | PASS |
| 8 | test_gesture_library_script_exists | PASS |
| 9 | test_render_script_exists | PASS |
| 10 | test_all_8_previews_exist | PASS |
| 11 | test_all_8_previews_640x360 | PASS |
| 12 | test_all_8_previews_above_20kb | PASS |
| 13 | test_all_8_previews_valid_png | PASS |
| 14 | test_aarav_greeting_action_exists | PASS |
| 15 | test_aarav_point_action_exists | PASS |
| 16 | test_aarav_wave_action_exists | PASS |
| 17 | test_aanya_greeting_action_exists | PASS |
| 18 | test_aanya_nod_action_exists | PASS |
| 19 | test_aanya_wave_action_exists | PASS |
| 20 | test_all_reports_exist | PASS |

Command run:
```
python -m pytest Local_3D_Cartoon_Studio/tests/test_stage4_2_movement.py -v --tb=short
```

---

## Stage 4.1 Regression Test Results

**Total: 13 tests — 13 PASSED, 0 FAILED**

| Test | Result |
|---|---|
| test_aarav_stage4_blend_exists | PASS |
| test_aanya_stage4_blend_exists | PASS |
| test_aarav_original_size | PASS |
| test_aanya_original_size | PASS |
| test_working_copies_differ_from_originals | PASS |
| test_aarav_idle_action_exists | PASS |
| test_aarav_walk_action_exists | PASS |
| test_aanya_idle_action_exists | PASS |
| test_aanya_walk_action_exists | PASS |
| test_all_previews_exist | PASS |
| test_all_previews_valid_png | PASS |
| test_all_previews_640x360 | PASS |
| test_all_previews_above_20kb | PASS |

Command run:
```
python -m pytest Local_3D_Cartoon_Studio/tests/test_stage4_1_animations.py -v --tb=short
```

**All Stage 4.1 functionality preserved.** The WALK action was improved (wider
thigh swing, hip sway, spine counter-rotation) but the action name `AARAV_WALK`
/ `AANYA_WALK` and frame range 1–36 are unchanged.

---

## Original File Integrity

| File | Expected Size | Actual Size | SHA-256 |
|---|---|---|---|
| `aarav.blend` | 774,392 bytes | 774,392 bytes | `CD70D788B702A31CE7F63673C13F95BB80E072CD9835E782BD5A7A473913B567` |
| `aanya.blend` | 796,228 bytes | 796,228 bytes | `C0DF05DB82F2C116C41E81EE5E6872B90253671E0E37FC3DFE37CB6B89A9EA72` |

Both original character files are unchanged.  Hashes were computed with
`Get-FileHash -Algorithm SHA256` before and after Stage 4.2 implementation.

---

## Working Copy Sizes

| File | Size after Stage 4.2 |
|---|---|
| `aarav_stage4.blend` | 796,866 bytes |
| `aanya_stage4.blend` | 818,702 bytes |

The increase from Stage 4.1 reflects the 5 new actions per character
(WAVE, POINT, NOD, GREETING, improved WALK) stored with `use_fake_user = True`.

---

## Known Limitations

1. **Option B mesh repositioning:** Only bones keyed in the action drive mesh
   movement.  Unkeyed limbs (e.g. the left arm during a right-arm gesture)
   stay at their rest positions unless explicitly keyed.

2. **Hip sway bone:** The `hips` bone is mapped to an empty mesh list in
   `_BONE_TO_MESH` because the rig uses a flat armature without a dedicated
   pelvis mesh.  Hip sway rotation is encoded in the thigh midpoints indirectly.

3. **Foot contact:** Approximated by shin/thigh keyframes.  Foot sliding may
   be visible at the wider ±0.5 rad thigh stride — a full IK foot lock was not
   implemented to avoid expensive simulation.

4. **Action discovery pattern:** Blender purges zero-user actions on file load.
   All gesture actions use `use_fake_user = True` to persist without NLA
   assignment.  The original IDLE and WALK actions have users via NLA strips
   created by `create_animations.py` and do not need fake user.

5. **Aanya orientation:** Both armatures have zero rotation.  The orientation
   fix in `render_stage42_previews.py` is defensive — it found no correction
   needed during Stage 4.2 rendering.

---

## Test Infrastructure Notes

- Blender-dependent tests use `@unittest.skipUnless(BLENDER_AVAILABLE, ...)`.
- Action existence tests are grouped per blend file (one Blender subprocess per
  group) to minimise overhead.
- All Blender subprocess calls use `subprocess.run(capture_output=True)` without
  `shell=True`, per project requirements.
