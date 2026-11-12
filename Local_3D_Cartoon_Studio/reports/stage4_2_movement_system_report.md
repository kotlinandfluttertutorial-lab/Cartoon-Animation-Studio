# Stage 4.2 — Movement System Report

**Project:** Local 3D Cartoon Animation Studio  
**Stage:** 4.2 — Character Movement, Interaction & Gesture System  
**Script:** `blender/scripts/character_movement.py`  
**Date:** 2026-11-11

---

## Overview

`character_movement.py` is a reusable Blender-internal module (runs inside `bpy`)
that provides character positioning, orientation control, Option B animation
application, and camera/scene setup utilities.  All functions follow the exact
patterns established in Stage 4.1 (`render_animation_preview.py`).

---

## Public API

### `face_direction(arm_obj, char_prefix, direction_vector, mesh_objects=None)`

Rotates the character to face a world-space direction vector.

**Implementation details:**
- Both characters rest facing **+Y** (nose at Y ≈ +0.265).
- The direction vector is projected onto the XY plane.
- The signed rotation angle around Z is computed as `atan2(dv.x, dv.y)` — note
  argument order `(x, y)` not `(y, x)` — which gives the angle from +Y to the
  target direction, measured clockwise around +Z.
- The angle is applied to the Z channel of the first available bone in the
  priority order: `hips → root → pelvis → spine`.
- If the direction vector has zero XY magnitude, the function is a no-op.

### `face_camera(arm_obj, char_prefix, camera_pos, mesh_objects=None)`

Convenience wrapper.  Computes direction from `arm_obj.location` to `camera_pos`
and delegates to `face_direction`.

### `face_target(arm_obj, char_prefix, target_pos, char_pos, mesh_objects=None)`

Convenience wrapper.  Computes direction from `char_pos` to `target_pos` and
delegates to `face_direction`.

### `move_to(char_objects, target_x, target_y)`

Moves all **parentless** objects of a character to `(target_x, target_y, 0)`.

**Implementation details:**
- Iterates `char_objects` and skips any object where `obj.parent is not None`.
- Sets `obj.location.x`, `obj.location.y`, `obj.location.z = 0` on matching objects.
- Calls `bpy.context.view_layer.update()` after all moves.
- Matches the combined-render pattern from `render_animation_preview.py` where
  each character's root objects are repositioned by X offset.

### `apply_action_pose(arm_obj, action_name, frame, char_prefix, mesh_objects=None)`

**Option B** implementation — identical to `apply_animation_pose()` in
`render_animation_preview.py`.

Steps:
1. Reset all pose bones to identity (XYZ Euler, zero rotation/location/scale).
2. Sample every `rotation_euler` fcurve in the named action at `frame` and apply
   to the matching pose bone.
3. Switch back to Object mode and call `bpy.context.view_layer.update()`.
4. Evaluate the depsgraph to get world-space bone positions.
5. For each keyed bone, look up mesh suffixes in `_BONE_TO_MESH`, read the
   bone's world-space midpoint `(head + tail) / 2` from the evaluated armature,
   and move the matching mesh object's `location` to that midpoint.
6. Call `bpy.context.view_layer.update()` again.

Returns `saved_locations` dict `{obj_name: original_location}`.

### `restore_pose(arm_obj, saved_locations)`

Restores mesh locations from `saved_locations` and resets all pose bones to
identity.  Exact pattern from `render_animation_preview.restore_pose()`.

### `setup_workbench(scene)`

Configures Workbench rendering:

| Parameter | Value |
|---|---|
| `render.engine` | `BLENDER_WORKBENCH` |
| `render.resolution_x` | 640 |
| `render.resolution_y` | 360 |
| `render.film_transparent` | False |
| `display.shading.light` | `STUDIO` |
| `display.shading.color_type` | `MATERIAL` |
| `display.shading.show_shadows` | True |

### `make_camera(scene, name, pos, target, lens=50)`

Creates a camera at `pos` looking at `target`.

**Implementation details:**
- Uses `direction.to_track_quat('-Z', 'Y').to_euler()` for rotation — identical
  to all existing render scripts.
- Links the camera object to `scene.collection.objects` and sets it as
  `scene.camera`.
- Returns the camera object.

---

## `_BONE_TO_MESH` Mapping

Taken verbatim from `render_animation_preview.py`:

| Bone | Mesh suffixes |
|---|---|
| `spine` | `Spine` |
| `chest` | `Chest` |
| `neck` | `Neck` |
| `head` | `Head` |
| `shoulder_L/R` | `Shoulder_L/R` |
| `upper_arm_L/R` | `UpperArm_L/R` |
| `forearm_L/R` | `LowerArm_L/R` |
| `hand_L/R` | `Hand_L/R` |
| `thigh_L/R` | `UpperLeg_L/R`, `Thigh_L/R` |
| `shin_L/R` | `LowerLeg_L/R`, `Shin_L/R` |
| `foot_L/R` | `Foot_L/R` |

---

## Option B Reuse

The Option B technique was established in Stage 2.1 (`render_character_preview.py`)
and formalised in Stage 4.1 (`render_animation_preview.py`).  Stage 4.2 reuses it
without modification:

- `character_movement.apply_action_pose` → mirrors `apply_animation_pose()`
- `character_movement.restore_pose` → mirrors `restore_pose()`
- `render_stage42_previews.py` embeds its own inline copy for self-containment
  (same code, independent of module import path)

---

## Camera Setup Parameters

| Scenario | Position | Target | Lens |
|---|---|---|---|
| Single character | `(0, 4.5, 0.875)` | `(0, 0, 0.875)` | 50 mm |
| Two characters | `(0, 6.0, 0.875)` | `(0, 0, 0.875)` | 40 mm |

Both cameras use **+Y** side placement (characters face +Y, camera is at +Y
looking toward -Y), consistent with Stage 4.1.

Target Z of 0.875 = half the character height of 1.75 BU, ensuring feet-to-head
framing at standard 640×360 resolution.
