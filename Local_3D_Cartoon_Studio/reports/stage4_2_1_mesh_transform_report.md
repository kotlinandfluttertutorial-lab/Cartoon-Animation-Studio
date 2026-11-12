# Stage 4.2.1 — Mesh Transform Preservation Architecture

## Mesh Transform Preservation Architecture

This project uses **Option B** for animating characters in Blender background mode. Because mesh objects are parented to the armature with **Object-type (rigid) parenting**, bone pose transforms do not automatically propagate to mesh object world positions. Instead, the pipeline:

1. Applies bone rotations from an action at a target frame
2. Evaluates the dependency graph to get world bone positions
3. Moves mesh objects to match the animated bone positions
4. Renders the frame
5. Restores all mesh objects to their original positions

The critical requirement is that step 3 preserves the original **spatial relationship** between each mesh origin and its controlling bone.

---

## Rest-Offset Computation (`compute_rest_offsets`)

### Purpose

`compute_rest_offsets(arm_obj, char_prefix)` computes the vector difference between each mesh object's world origin and its controlling bone's world midpoint **in rest pose** (all bones at identity).

This offset encodes the original design intent of the character rig — how far each mesh piece is displaced from the center of its bone.

### Algorithm

```
1. Reset all pose bones to identity (zero rotation, zero location, unit scale)
2. Force depsgraph update
3. For each bone in _BONE_TO_MESH:
   a. Compute bone world midpoint = (mw @ head + mw @ tail) * 0.5
   b. For each mesh suffix → obj_name = f'{char_prefix}_{suffix}':
      offset[obj_name] = obj.location - bone_midpoint
4. Return offsets dict
```

### Usage Pattern

```python
# Call once per character, in rest pose, before any animation is applied
rest_offsets = compute_rest_offsets(arm_obj, 'Aarav')

# Pass to every apply_action_pose() call for this character
saved = apply_action_pose(arm_obj, 'AARAV_WAVE', 6, 'Aarav',
                          rest_offsets=rest_offsets)
```

If `rest_offsets` is not provided, `apply_action_pose()` computes them internally (slower — requires a pose reset/reapply cycle).

---

## Safe-Bones Restriction (Why Head/Neck/Spine Excluded)

### The Problem

In rigid-parenting mode, moving the `head` mesh object to a raw bone midpoint without the correct offset causes visible detachment because:
- The head bone midpoint is typically at the center of the neck-to-crown range
- The actual head mesh origin is offset upward and forward
- In a nod gesture, this offset change is amplified by the rotation

The same applies to `neck`, `spine`, `chest`, and `shoulder` bones.

### The Solution: `_SAFE_BONES`

```python
_SAFE_BONES = frozenset({
    'upper_arm_L', 'forearm_L', 'hand_L',
    'upper_arm_R', 'forearm_R', 'hand_R',
    'thigh_L', 'shin_L', 'foot_L',
    'thigh_R', 'shin_R', 'foot_R',
})
```

Only arm and leg bones are included. These are the bones that move significantly during gestures (wave, point) and walk cycles. Their mesh offsets are small and predictable.

Excluded bones:
- `head`, `neck` — NOD gesture; head mesh excluded from Option B movement
- `spine`, `chest` — Torso; remains at rest position
- `shoulder_L`, `shoulder_R` — Small rotation, excluded to prevent shoulder pop
- `hips` — Root bone; character position handled by object-level translation

### Trade-off

For gestures that primarily involve arm movement (WAVE, POINT, GREETING), the fix produces clean results. For NOD (which moves the head bone), the bone receives the correct rotation but the head mesh object stays in rest position in still renders. This is a **documented limitation** — see the visual defect analysis report.

---

## Before vs After Comparison

### Before (Stage 4.2 — Broken)

```python
# In apply_animation_pose():
obj.location = midpoint  # WRONG — no offset, no bone filtering
```

**Result:** Mesh objects snap to raw bone midpoints regardless of original placement. Head, spine, chest, and shoulder meshes detach from body. All 8 previews show visual artifacts.

### After (Stage 4.2.1 — Fixed)

```python
# In apply_action_pose():
if bone_name not in _SAFE_BONES:
    continue  # skip head/neck/spine — prevents detachment
offset = rest_offsets.get(obj_name, mathutils.Vector((0.0, 0.0, 0.0)))
obj.location = midpoint + offset  # CORRECT — preserves rest relationship
```

**Result:** Only arm/leg meshes move. Each mesh maintains its original spatial relationship to its bone. All 12 Stage 4.2.1 previews render without detachment.

---

## Aanya Facing Direction Analysis and Camera Correction

### Probe Results

Blender background probe on `aanya_stage4.blend`:
```
ARM_ROT: (0.0, 0.0, 0.0)   # Aanya_Armature has zero rotation
NOSE_LOC: (0.0, -0.32, 1.37)  # nose is at Y = -0.32
```

For comparison, Aarav's nose should be at Y = +0.265 (faces +Y). Aanya's nose at Y = -0.32 means her mesh geometry faces **-Y** (away from the camera at +Y).

The armature rotation being zero confirms this is a geometry-level orientation, not an armature rotation issue. The mesh objects themselves were modeled or exported facing -Y.

### Correction Applied

**Single-character renders:** `fix_aanya_single_orientation()` applies a 180° Z rotation to all parentless Aanya objects before computing rest offsets and rendering.

**Combined renders:** `fix_aanya_orientation()` in `render_stage421_previews.py` always applies the 180° flip. It also checks for any additional armature Z rotation and counter-rotates if present (for future-proofing).

**Order of operations (critical):**
1. Apply 180° orientation fix
2. Apply X-offset for character positioning
3. Compute rest offsets (so offsets are computed at final orientation)
4. Apply action pose
5. Render
6. Restore pose
