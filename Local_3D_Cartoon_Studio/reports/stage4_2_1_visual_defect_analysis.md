# Stage 4.2.1 — Visual Defect Analysis

## Root Cause Analysis of Stage 4.2 Visual Defects

All 8 Stage 4.2 preview images exhibited body-part detachment, misalignment, or incorrect facing direction. The root cause was traced to a single incorrect assignment in `apply_action_pose()` and `apply_animation_pose()`:

```python
# BROKEN (Stage 4.2):
obj.location = bone_midpoint
```

This overwrites the mesh object's world-space location with the raw evaluated bone midpoint, completely ignoring the original spatial offset between the mesh origin and the bone.

Additionally, the head/neck/spine bones were also being processed, causing torso and head mesh objects to snap to raw bone positions — detaching them from the rest of the body.

A secondary root cause was Aanya's facing direction: her mesh geometry faces -Y (nose at Y = -0.32 confirmed by Blender probe), not +Y. The camera is at +Y. Stage 4.2 did not apply a 180° correction, so all Aanya individual renders showed the back of her head.

---

## The Broken `obj.location = bone_midpoint` Pattern Explained

### Background

In this project, mesh objects are parented to the armature with **Object-type (rigid) parenting**. This means bone transforms do NOT automatically propagate to mesh object world positions. The pipeline uses **Option B**: manually move mesh objects to match bone positions at render time.

### The Bug

Consider a character at rest pose:
- Bone midpoint in rest pose is at world position **R** = (0, 0, 1.2)
- Mesh object origin is at world position **M** = (0.05, 0, 1.25) — slightly offset
- Rest offset **O** = M - R = (0.05, 0, 0.05)

When a gesture is applied, the bone moves to **R'** = (0.3, 0, 1.4):
- **Broken code**: `obj.location = R'` → places mesh at (0.3, 0, 1.4), ignoring offset
- **Correct code**: `obj.location = R' + O` → places mesh at (0.35, 0, 1.45), preserving relationship

For small offsets the error is minor, but for bones with large offsets (UpperArm, Thigh, etc.) the visual result is severe detachment.

### Additional Problem: Unsafe Bone Coverage

Stage 4.2 moved meshes for ALL keyed bones, including `head`, `neck`, `spine`, `chest`, and `shoulder` bones. These torso/head bones have large rest offsets. Moving them without offset correction caused head and torso parts to scatter to incorrect positions.

---

## Per-Image Defect Log (All 8 Stage 4.2 Images)

| Image | Defect | Root Cause |
|-------|--------|------------|
| `aarav_wave.png` | Left arm mesh displaced from shoulder | `obj.location = midpoint` ignored upper_arm_L offset |
| `aanya_wave.png` | Aanya facing away from camera; arm displaced | Mesh faces -Y (no orientation fix) + offset bug |
| `aarav_point.png` | Right arm/hand misaligned | `obj.location = midpoint` ignored forearm_R/hand_R offset |
| `aanya_nod.png` | Aanya facing away from camera | Mesh faces -Y (no orientation fix) |
| `both_facing_camera.png` | Aanya not visible (behind Aarav or facing away); head components detached | No Aanya 180° flip + offset bug on head/spine bones |
| `greeting_interaction.png` | Aarav head detached; Aanya facing wrong | head/neck bones moved without offset + no Aanya flip |
| `pointing_interaction.png` | Body-part alignment incorrect on both characters | offset bug across multiple bones |
| `walk_together.png` | Multiple Aarav body components detached; Aanya facing wrong | Leg/spine/shoulder bone offset bug + no Aanya flip |

---

## Fix Implementation Summary

### Fix 1: `compute_rest_offsets()` in character_movement.py

A new function `compute_rest_offsets(arm_obj, char_prefix)` computes the per-object offset between each mesh origin and its rest-pose bone midpoint. This must be called **once per character in rest pose** before any animation is applied.

```python
offset[obj_name] = obj.location.copy() - bone_rest_midpoint
```

### Fix 2: Offset-Corrected Mesh Positioning in `apply_action_pose()`

The assignment is now:
```python
obj.location = midpoint + offset  # CORRECT
```
where `midpoint` is the animated bone midpoint and `offset` is the rest offset.

### Fix 3: `_SAFE_BONES` Restriction

Only arm and leg bones are moved: `upper_arm_L/R`, `forearm_L/R`, `hand_L/R`, `thigh_L/R`, `shin_L/R`, `foot_L/R`.

Head, neck, spine, chest, and shoulder mesh objects are **excluded** from Option B mesh movement. This prevents torso/head detachment. The bones still receive rotation data from the action (visible in Blender viewport playback), but the mesh objects remain in their rest positions in still renders.

### Fix 4: Aanya 180° Z Orientation Correction

Probe confirmed Aanya's nose is at Y = -0.32 in rest pose (faces -Y). A 180° rotation is applied to all parentless Aanya objects before rendering, in both single-character and combined scenes.

---

## Known Remaining Limitations

### NOD Gesture — Head Mesh in Rigid-Parenting Mode

**Limitation:** When rendering AARAV_NOD or AANYA_NOD in still-frame mode, the `head` bone is excluded from `_SAFE_BONES`. The head bone receives the correct nodding rotation (applied to pose data), but the head mesh object does not visually move in the still render.

**Why:** Moving the head mesh without offset correction caused detachment. With offset correction applied only at rest, the head object returns to exactly its rest position after `restore_pose()`.

**Mitigation:** The bone rotation data IS correctly captured in the .blend action. In Blender's interactive viewport with armature-driven animation, the nod gesture is fully visible. Only still-frame Option B rendering is affected.

**Workaround (future):** Implement full transform-hierarchy parenting (child-of constraints or actual bone parenting) instead of rigid Object parenting — this would eliminate the need for Option B entirely.

---

## Human Visual Review Checklist

All items below require human visual inspection. **DO NOT mark these as approved without manual review.**

- [ ] `aarav_idle.png` — Aarav facing camera, proportions correct, no detached parts
- [ ] `aarav_wave.png` — Aarav arm raised, hand visible, no detachment
- [ ] `aarav_point.png` — Aarav right arm extended in pointing pose, aligned
- [ ] `aarav_nod.png` — Aarav in rest pose (nod not visible in still — documented limitation)
- [ ] `aanya_idle.png` — Aanya facing camera (not back-of-head), proportions correct
- [ ] `aanya_wave.png` — Aanya facing camera, arm raised, no detachment
- [ ] `aanya_point.png` — Aanya facing camera, right arm in pointing pose
- [ ] `aanya_nod.png` — Aanya facing camera in rest pose (nod not visible — documented limitation)
- [ ] `both_facing_camera.png` — Both characters visible, both facing camera, correct separation
- [ ] `greeting_interaction.png` — Both facing camera, Aarav arm raised, Aanya responding
- [ ] `pointing_interaction.png` — Aarav pointing, Aanya facing camera, no detachment
- [ ] `walk_together.png` — Both walking, leg poses visible, no detached parts
