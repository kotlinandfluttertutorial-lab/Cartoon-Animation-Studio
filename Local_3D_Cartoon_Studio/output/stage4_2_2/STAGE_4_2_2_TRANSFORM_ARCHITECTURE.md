# Stage 4.2.2 Transform Architecture

## Problem

Blender's standard armature deformation relies on mesh objects being parented to bones with `parent_type=BONE`. When a bone rotates, any mesh objects with bone parenting automatically inherit the transform through the depsgraph.

The Aarav and Aanya characters were built with rigid object parenting (`parent_type=OBJECT`). In this mode the armature is the parent object, but mesh objects do not inherit individual bone transforms — they stay at their rest-pose world-space locations regardless of what the bones do. This means that in Blender background mode (no viewport, no modifier stack applied to the render mesh), animated bone rotations produce no visible change in mesh positions unless explicit code moves the mesh objects after evaluating the depsgraph.

This is not a bug in the rig; it is the established design of these assets. Any transform solution must work within it.

---

## Stage 4.2.1 Approach

Stage 4.2.1 introduced Option B: a manual mesh-repositioning pipeline that:

1. Resets all bones to identity (rest pose) and records each mesh object's rest-pose world location relative to its controlling bone's midpoint — the **rest offset**.
2. Applies the target action at the target frame by sampling each bone's `rotation_euler` f-curves and writing the values directly to `pose.bones[name].rotation_euler`.
3. Forces a depsgraph update and reads the **evaluated** (animated) bone midpoints in world space.
4. Moves each mesh object to `new_bone_midpoint + rest_offset`, preserving the original spatial relationship.
5. Renders the still frame and immediately restores all mesh locations and bone rotations.

The key safety constraint in Stage 4.2.1 was `_SAFE_BONES` — a frozenset that controlled which bones triggered mesh repositioning. Only arm and leg bones were included:

```
upper_arm_L, forearm_L, hand_L
upper_arm_R, forearm_R, hand_R
thigh_L, shin_L, foot_L
thigh_R, shin_R, foot_R
```

Head and neck were explicitly excluded as a conservative measure because their mesh objects had not been tested with Option B at that time.

---

## Stage 4.2.2 Approach

Stage 4.2.2 extends `_SAFE_BONES` to include `'head'` and `'neck'`:

```python
_SAFE_BONES = frozenset({
    'neck', 'head',
    'upper_arm_L', 'forearm_L', 'hand_L',
    'upper_arm_R', 'forearm_R', 'hand_R',
    'thigh_L', 'shin_L', 'foot_L',
    'thigh_R', 'shin_R', 'foot_R',
})
```

The `_BONE_TO_MESH` mapping for the `'head'` bone is updated to include Aanya's Hijab:

```python
'head': ['Head', 'Hijab'],
```

The NOD action angles in `gesture_library.py` are increased so that the visible head tilt at the peak frame (frame 4) is approximately 29° (0.5 rad), well above the 0.4 rad test threshold.

No other part of the Option B pipeline changes. The same `compute_rest_offsets` and `apply_action_pose` functions that correctly reposition arm and leg meshes now also correctly reposition head and neck meshes.

---

## Why It Is Safe

The safety of extending Option B to head and neck rests on a single verified property: both mesh objects have `parent_type=OBJECT`, not `parent_type=BONE`.

**Probe result** (`probe_results.json`, collected before any Stage 4.2.2 changes):

| Object | `parent_type` |
|---|---|
| `Aarav_Head` | `OBJECT` |
| `Aarav_Neck` | `OBJECT` |
| `Aanya_Head` | `OBJECT` |
| `Aanya_Neck` | `OBJECT` |

Because these objects use rigid object parenting:

- They do **not** receive bone transforms automatically — there is no existing bone transform to interact with.
- Moving `obj.location` directly is the only way to reflect bone movement in the render.
- The offset correction produces no double-transformation because the depsgraph does not apply a bone transform to these objects before or after the location write.

This is precisely the same situation as the arm and leg mesh objects, which passed all Stage 4.2.1 tests without detachment. Adding head and neck to `_SAFE_BONES` applies the same proven logic to them.

---

## Offset Correction Formula

For each mesh object associated with a bone in `_SAFE_BONES`:

```
rest_offset   = rest_mesh_location − rest_bone_midpoint
new_position  = new_bone_midpoint  + rest_offset
```

Where:

- `rest_mesh_location` is `obj.location` with all bones at identity (sampled once by `compute_rest_offsets`).
- `rest_bone_midpoint` is `(bone.head_world + bone.tail_world) / 2` with all bones at identity.
- `new_bone_midpoint` is the same midpoint expression after applying the action at the target frame and updating the depsgraph.

This formula preserves the original spatial relationship between the mesh origin and its controlling bone midpoint under any rotation or translation of the bone.

---

## Aanya Hijab

`Aanya_Hijab` is a free mesh object (no bone parenting) that visually belongs to Aanya's head. Because it uses `parent_type=OBJECT` with the armature as parent, it does not follow the head bone automatically.

In Stage 4.2.2, `'Hijab'` is added to the `_BONE_TO_MESH['head']` list alongside `'Head'`. The offset correction is applied identically:

1. `compute_rest_offsets` records the offset of `Aanya_Hijab` relative to the head bone midpoint in rest pose.
2. `apply_action_pose` moves `Aanya_Hijab` to `new_head_bone_midpoint + hijab_rest_offset` at render time.
3. `restore_pose` returns `Aanya_Hijab` to its original location.

For Aarav, `bpy.data.objects.get('Aarav_Hijab')` returns `None` and the entry is silently skipped — no special-casing or character-name branching is required.

---

## Comparison with Alternatives

### Bone parenting (`parent_type=BONE`)

Changing mesh objects from `parent_type=OBJECT` to `parent_type=BONE` would allow automatic bone-transform inheritance, but it would also require saving modified `.blend` files for every character. The existing rig was designed with object parenting throughout; changing it risks breaking established rest-pose offsets, the proven render pipeline from Stages 4.1 and 4.2, and any downstream scripts that depend on the current parent relationships. The risk-to-benefit ratio is unfavourable given that Option B already delivers the required result.

### Child Of constraints

A `Child Of` constraint on each mesh object pointing at its controlling bone would propagate bone transforms to the mesh. However, constraint evaluation requires saving modified blend files, interacts non-trivially with the existing object parenting, and would require understanding the inverse matrix state of each constraint at the time of application. No clear advantage over the existing approach.

### Evaluated dependency-graph matrix

Reading `obj.evaluated_get(depsgraph).matrix_world` and applying it to the original mesh position is a more general approach that handles arbitrary constraint stacks. It is also more complex to implement correctly, particularly when the character has the established 180° Z-rotation correction for Aanya. It offers no accuracy advantage over the offset midpoint approach for the current rig, since the mesh objects have no additional constraints beyond their armature parenting.

### Parent inverse matrices

Blender stores `parent_inverse` on each object to account for the parent's transform at the time of parenting. Using this directly would require constructing the full world transform from bone pose matrices, which duplicates what the depsgraph already computes. The midpoint approach is simpler and relies on the depsgraph to do the heavy lifting.

---

## Why Stage 4.2.1 Excluded Head

Stage 4.2.1 excluded head and neck from `_SAFE_BONES` for two reasons:

1. **No probe data at the time.** The `parent_type` of head and neck mesh objects had not been confirmed to be `OBJECT`. The conservative choice was to exclude any bone whose mesh objects had not been tested.
2. **Incremental risk management.** Stage 4.2.1 was primarily about fixing arm and leg displacement, which had been confirmed as broken. Extending the fix to head and neck without proof would have widened the scope and introduced untested risk. Documenting the limitation and deferring it to Stage 4.2.2 kept each stage's changes minimal and verifiable.

Stage 4.2.2 resolves the limitation with the probe confirmation in hand.
