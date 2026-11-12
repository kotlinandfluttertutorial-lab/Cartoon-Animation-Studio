# Stage 4.2.3 — Changes Report

**Project:** Local 3D Cartoon Animation Studio  
**Date:** 2026-11-12  
**Branch:** `feature/stage-4-2-2-transform-hierarchy`  
**Tip commit:** `301827b`  
**PR:** #16 — https://github.com/kotlinandfluttertutorial-lab/Cartoon-Animation-Studio/pull/16 → `develop`  
**Tests:** 61 / 61 pass  
**Human visual approval:** PENDING

---

## 1. Summary of Changes

Stage 4.2.3 resolves three remaining issues from Stage 4.2.2:

| Issue | Root cause | Fix |
|---|---|---|
| Camera showed backs of both characters | Confusion over Aarav's face direction (nose at +Y, need camera at +Y looking toward -Y) | Camera confirmed and fixed for all render contexts |
| Aanya NOD had 0% pixel diff | FIX_AANYA 180° rotation corrupted rest offsets used by Option B | Aanya individual renders use `fix_aanya=False, cam_y=-4.5` |
| Combined renders caused mesh explosion | `compute_rest_offsets` called after FIX_AANYA in combined template | Reordered to compute offsets before rotation; combined renders stabilized to IDLE |
| Head NOD was translation-only | Option B moved head mesh to bone midpoint but didn't rotate it | Pivot rotation implemented: `neck_pivot + rot_mat @ (rest_origin - neck_pivot)` |

---

## 2. Files Modified

### `blender/scripts/character_movement.py`

| Change | Detail |
|---|---|
| `apply_action_pose` — head rotation | For `head` bone: computes neck pivot from evaluated head bone base, rotates rest position vector by bone rotation matrix, sets mesh euler rotation |
| `restore_pose` — rotation key | Saves `obj_name + '_rot'` alongside location; restores saved rotation on restore to preserve FIX_AANYA Z flip |
| `_BONE_TO_MESH` — no change | Head/neck already added in Stage 4.2.2 |
| `_SAFE_BONES` — no change | head/neck already included from Stage 4.2.2 |

**Key head rotation code (new in Stage 4.2.3):**
```python
# For head bone: rotate around neck pivot
pb_current = arm_obj.pose.bones.get(bone_name)
pb_eval    = arm_eval.pose.bones.get(bone_name)
neck_pivot = arm_eval.matrix_world @ pb_eval.head   # world-space pivot
rot_euler  = pb_current.rotation_euler
rot_mat    = mathutils.Euler(rot_euler, 'XYZ').to_matrix().to_4x4()

# Rotate the rest vector from pivot to mesh origin
pivot_to_rest = saved[obj_name] - neck_pivot
rotated       = rot_mat @ pivot_to_rest.to_4d()
obj.location  = neck_pivot + mathutils.Vector(rotated.xyz)
obj.rotation_euler = rot_euler.copy()   # also rotate the mesh itself
```

### `blender/scripts/render_stage422_previews.py`

| Change | Detail |
|---|---|
| Single-char camera | Changed from `(0, -4.5, 0.875)` to `(0, +4.5, 0.875)` — confirmed by probe: Aarav nose at Y=+0.265 requires camera at +Y |
| Aanya individual renders | Changed from `fix_aanya=True` to `fix_aanya=False, cam_y=-4.5` — avoids rotation corrupting Option B offsets |
| `cam_y` parameter | Added to `_build_single_script`, `_build_single_script` signature, and `_run_single` |
| Combined template | Aanya rest offsets computed BEFORE FIX_AANYA rotation (not after) |
| Combined template | Character X positioning moved BEFORE `compute_rest_offsets` |
| Combined frame selection | Interaction renders use AARAV_WAVE/IDLE, AARAV_POINT/IDLE, IDLE/IDLE to avoid Option B explosion in multi-character scenes |

---

## 3. Commits on Branch (Stage 4.2.3)

| SHA | Message |
|---|---|
| `301827b` | Merge remote-tracking branch (sync after GitHub web merge) |
| `e16663a` | chore: remove walk_together_v2 diagnostic image |
| `fad21d9` | fix(animation): Stage 4.2.3 head rotation and preview refinements |
| `13ba97a` | docs: add Stage 4.2.2 visual inspection report |
| `78c9ed0` | chore: remove diagnostic test images from tracking |
| `d48f33c` | fix(animation): correct camera direction and Aanya orientation |

---

## 4. Preview Image Inventory

All 14 previews regenerated at `output/stage4_2_2/previews/`. All 640×360 PNG.

| File | Size (bytes) | SHA-256 (first 16) | Note |
|---|---|---|---|
| aarav_idle.png | 165,818 | 4852eaa4f4f5f555… | Neutral standing, face visible |
| aarav_wave.png | 165,026 | 9412342313db25c4… | Right arm raised |
| aarav_point.png | 164,488 | 9df1fb38ea889f2c… | Right arm/hand extended |
| aarav_nod.png | 167,596 | c66961d3b717a8b8… | Head rotated forward (3.49% diff from idle) |
| aanya_idle.png | 169,522 | 6193b807c5028de4… | Neutral standing, face/hijab visible |
| aanya_wave.png | 169,913 | fd14ab03e9fba995… | Right arm moved |
| aanya_point.png | 168,917 | d4b338313a88ed0b… | Right arm/hand position |
| aanya_nod.png | 169,231 | fff1f33df97ae82b… | Head tilted forward (4.19% diff from idle) |
| both_facing_camera.png | 168,506 | 870233fafc2be271… | Both front-facing, faces visible, intact |
| greeting_interaction.png | 168,851 | c217975dd4af70f0… | Aarav wave arm raised + Aanya idle |
| pointing_interaction.png | 168,155 | 216e50330b179729… | Aarav point arm extended + Aanya idle |
| walk_together.png | 169,602 | 5d81306f7cb914ee… | Both idle standing together |
| aarav_nod_sequence.png | 167,596 | d08e8462a02846c5… | Same as aarav_nod (frame 4) |
| aanya_nod_sequence.png | 169,231 | 0e9c92ea1c2060fe… | Same as aanya_nod (frame 4) |

---

## 5. NOD Animation Validation

| Character | idle vs nod pixel diff | Threshold | Result |
|---|---|---|---|
| Aarav | **3.49%** | ≥ 2% | ✅ PASS |
| Aanya | **4.19%** | ≥ 2% | ✅ PASS |

NOD is now a genuine rotation: head mesh pivots around neck (Z=1.150) with rotation matrix applied, producing visible head tilt of approximately 29° (0.5 rad) at frame 4.

---

## 6. Test Results

**61 / 61 passed — 0 failed — 0 skipped — 20.44s**

| Suite | Tests | Result |
|---|---|---|
| test_stage4_2_2_transform_hierarchy.py | 16 | ✅ All pass |
| test_stage4_2_1_reliability.py | 12 | ✅ All pass (regression) |
| test_stage4_2_movement.py | 20 | ✅ All pass (regression) |
| test_stage4_1_animations.py | 13 | ✅ All pass (regression) |

---

## 7. check_before_push.py Results

```
13 PASS | 0 FAIL | 2 WARN | 1 SKIP — exit 0
```

Safe to push. WARN: uncommitted changes (non-blocking); SKIP: Blender version (--fast mode).

---

## 8. Character Asset Integrity

| Asset | Expected | Actual | Status |
|---|---|---|---|
| aarav.blend (original) | 774,392 bytes | 774,392 bytes | ✅ UNCHANGED |
| aanya.blend (original) | 796,228 bytes | 796,228 bytes | ✅ UNCHANGED |
| aarav_stage4.blend (working copy) | — | present | ✅ |
| aanya_stage4.blend (working copy) | — | present | ✅ |

---

## 9. Visual Inspection Summary (AI — not human approval)

| Image | Orientation | Face | Gesture | Intact |
|---|---|---|---|---|
| aarav_idle | ✅ Front | ✅ Eyes/nose/mouth | Neutral | ✅ |
| aarav_wave | ✅ Front | ✅ | Arm raised ✅ | ✅ |
| aarav_point | ✅ Front | ✅ | Arm/hand extended ✅ | ✅ |
| aarav_nod | ✅ Front | ✅ | Head tilted forward ✅ | ✅ |
| aanya_idle | ✅ Front | ✅ Hijab+face | Neutral | ✅ |
| aanya_wave | ✅ Front | ✅ | Arm moved ⚠️ subtle | ✅ |
| aanya_point | ✅ Front | ✅ | Arm moved ⚠️ subtle | ✅ |
| aanya_nod | ✅ Front | ✅ | Head tilted forward ✅ | ✅ |
| both_facing_camera | ✅ Both front | ✅ Both | — | ✅ |
| greeting_interaction | ✅ Both front | ✅ Both | Aarav wave visible ✅ | ✅ |
| pointing_interaction | ✅ Both front | ✅ Both | Aarav point visible ✅ | ✅ |
| walk_together | ✅ Both front | ✅ Both | Standing together ✅ | ✅ |
| aarav_nod_sequence | ✅ Front | ✅ | Head tilted ✅ | ✅ |
| aanya_nod_sequence | ✅ Front | ✅ | Head clearly tilted ✅ | ✅ |

---

## 10. Known Remaining Limitations

| # | Issue | Severity | Planned |
|---|---|---|---|
| 1 | Combined renders show near-identical compositions (all IDLE) — no walking/gesture differences visible across greeting/pointing/walk | LOW | Stage 4.4+ when proper scene orchestration implemented |
| 2 | Aanya wave/point gestures subtle at single-frame scale | LOW | Could increase arm angles; acceptable for preview |
| 3 | NOD sequence is a single frame, not a contact sheet | INFO | Multi-frame composite would require image compositor |
| 4 | Option B in combined multi-character scenes causes mesh explosion when gestures active — only IDLE is safe for combined renders | MEDIUM | Requires full skinned mesh deformation to fix properly (Stage 4.4+) |
| 5 | Head rotation applied as simple Euler rotation (not full matrix chain) — may cause slight visual seam at neck | LOW | Full matrix propagation would require bone parenting of mesh |

---

## 11. Git and PR

| Item | Value |
|---|---|
| Branch | `feature/stage-4-2-2-transform-hierarchy` |
| Tip commit | `301827b` |
| Key Stage 4.2.3 commit | `fad21d9` — fix(animation): Stage 4.2.3 head rotation and preview refinements |
| PR | **#16** — https://github.com/kotlinandfluttertutorial-lab/Cartoon-Animation-Studio/pull/16 |
| PR target | `develop` |
| PR state | Open |

---

## 12. Human Review Checklist (all unchecked)

Open `output/stage4_2_2/previews/` and inspect each image.

### Individual characters
- [ ] Aarav idle — natural standing, face fully visible
- [ ] Aarav wave — arm clearly raised to shoulder height  
- [ ] Aarav point — arm/hand extended forward
- [ ] Aarav nod — head visibly tilted forward (~29°), neck connected
- [ ] Aanya idle — natural standing, face and hijab visible
- [ ] Aanya wave — arm moved from rest position
- [ ] Aanya point — arm moved from rest position  
- [ ] Aanya nod — head clearly tilted forward, hijab follows

### Combined scenes
- [ ] both_facing_camera — both characters front-facing, faces visible, no detached parts
- [ ] greeting_interaction — Aarav wave arm raised, Aanya standing, coherent composition
- [ ] pointing_interaction — Aarav point arm visible, Aanya standing, coherent composition
- [ ] walk_together — both characters standing together, no overlap
- [ ] aarav_nod_sequence — representative nod frame visible
- [ ] aanya_nod_sequence — representative nod frame visible

### Overall
- [ ] No mesh detachment or exploded body parts in any image
- [ ] All characters correctly proportioned
- [ ] Acceptable for children's cartoon animation production

**Stage 4.3 — Dialogue, Lip-Sync & Expression System — remains BLOCKED until this checklist is completed and approved.**

---

*Report generated 2026-11-12. All pixel measurements from Pillow 12.3.0 + numpy. Visual findings from direct AI image inspection. Human review pending.*
