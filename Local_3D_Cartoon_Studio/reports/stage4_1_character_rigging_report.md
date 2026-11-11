# Stage 4.1 — Character Rigging and Animation Foundation Report

## Overview

Stage 4.1 implements reusable character animations for Aarav and Aanya using their
existing 20-bone armature rigs. Two animation actions (IDLE and WALK) were created for
each character and embedded in stage4 working copy blend files. Five animation preview
renders were produced to validate the animation pipeline.

---

## 1. Rig Audit

### Existing Armature Structure (confirmed from character.json)

Both characters share an identical 20-bone armature layout:

| Region | Bones |
|--------|-------|
| Core   | root, hips, spine, chest, neck, head |
| Left arm | shoulder_L, upper_arm_L, forearm_L, hand_L |
| Right arm | shoulder_R, upper_arm_R, forearm_R, hand_R |
| Left leg | thigh_L, shin_L, foot_L |
| Right leg | thigh_R, shin_R, foot_R |

**Total: 20 bones per character**

### Parenting Type

Both characters use **rigid OBJECT parenting** (`parent_type='OBJECT'`) — each body part
mesh is parented to the armature as a whole, not to individual bones with vertex groups.
This means bone rotations do NOT deform meshes via skinning weights.

### Animation Implications

Since vertex group/skinning is not in use, two valid approaches exist:

| Approach | Complexity | Used |
|----------|-----------|------|
| Vertex group weight painting | High (requires manual weight paint per bone) | No |
| Direct object animation (Option B) | Low (move meshes to evaluated bone midpoints) | **Yes** |

The **Option B** technique, already proven in Stage 2.1 for the wave pose preview, was
adopted: pose bones are set, the depsgraph is evaluated, and mesh objects are moved to
the world-space midpoints of the corresponding evaluated bones for rendering.

---

## 2. Working Copy Creation

| File | Source | Size | Status |
|------|--------|------|--------|
| `aarav/aarav_stage4.blend` | `aarav/aarav.blend` (774,392 bytes) | 783,569 bytes | ✅ Created |
| `aanya/aanya_stage4.blend` | `aanya/aanya.blend` (796,228 bytes) | 805,405 bytes | ✅ Created |

Working copies are larger because they contain embedded animation actions and NLA track
data. Original files remain byte-for-byte identical to their pre-Stage 4 sizes.

---

## 3. Animation Implementation

### Script: `create_animations.py`

Creates `{NAME}_IDLE` and `{NAME}_WALK` actions in a stage4 blend file via Blender
background mode. Idempotent: re-running removes and recreates actions rather than
duplicating them.

**Execution:**
```
blender --background <stage4_blend> --python create_animations.py -- <stage4_blend> <CharacterName>
```

### IDLE Action Specification

| Action | Frames | Duration | FPS |
|--------|--------|----------|-----|
| AARAV_IDLE | 1–48 | 2.0 s | 24 |
| AANYA_IDLE | 1–48 | 2.0 s | 24 |

Keyframes (rotation_euler values in radians):

| Frame | Bone   | Channel | Value   |
|-------|--------|---------|---------|
| 1     | spine  | Y       | 0.000   |
| 1     | head   | Z       | 0.000   |
| 12    | spine  | Y       | +0.030  |
| 12    | head   | Z       | +0.020  |
| 24    | spine  | Y       | 0.000   |
| 24    | head   | Z       | 0.000   |
| 36    | spine  | Y       | −0.020  |
| 36    | head   | Z       | −0.020  |
| 48    | spine  | Y       | 0.000   |
| 48    | head   | Z       | 0.000   |

Total: 2 fcurves × 5 keyframe points = **10 keyframe points** per IDLE action.

### WALK Action Specification

| Action | Frames | Duration | FPS |
|--------|--------|----------|-----|
| AARAV_WALK | 1–36 | 1.5 s | 24 |
| AANYA_WALK | 1–36 | 1.5 s | 24 |

Key frames follow alternating leg/arm stride cycle:

| Frame | Description |
|-------|-------------|
| 1     | Stride A: thigh_L forward, thigh_R back, arms counter-swing |
| 9     | Passing: all limbs at neutral |
| 18    | Stride B: thigh_R forward, thigh_L back (opposite of frame 1) |
| 27    | Passing: all limbs at neutral |
| 36    | Same as frame 1 (seamless loop) |

Shin bounce adds realism: `shin_L/shin_R` bend slightly (X=−0.2) when the corresponding
thigh swings forward, simulating knee lift.

Bones keyed: `thigh_L`, `thigh_R`, `upper_arm_L`, `upper_arm_R`, `shin_L`, `shin_R`

Total: 6 fcurves × 5 keyframe points = **30 keyframe points** per WALK action.

### NLA Setup

Each action is pushed to an NLA track on the armature:
- `AARAV_IDLE_NLA` / `AANYA_IDLE_NLA` — cyclic, frames 1–48
- `AARAV_WALK_NLA` / `AANYA_WALK_NLA` — cyclic, frames 1–36

---

## 4. Preview Renders

Script: `render_animation_preview.py`

Uses BLENDER_WORKBENCH engine, 640×360, front camera at `(0, −4.0, 0.80)` targeting
`(0, 0, 0.80)` — identical to the proven wave pose camera from Stage 2.1.

| Output File | Source | Frame | Action |
|-------------|--------|-------|--------|
| `aarav_idle.png` | Aarav | 12 | AARAV_IDLE |
| `aarav_walk.png` | Aarav | 1 | AARAV_WALK |
| `aanya_idle.png` | Aanya | 12 | AANYA_IDLE |
| `aanya_walk.png` | Aanya | 1 | AANYA_WALK |
| `both_characters_animation.png` | Both | 1 | AARAV_WALK + AANYA_WALK |

Combined render: Aanya's objects appended via `bpy.data.libraries.load`, characters
offset ±0.8 BU on X-axis, camera pulled back to Y=−5.5 with 40mm lens.

All 5 PNGs: 640×360, >20 KB (actual range: 167–176 KB).

---

## 5. Known Limitations

1. **Mesh deformation**: Body parts are rigid objects — limbs do not bend/deform at
   joints. Each bone segment moves as a solid unit. For fully deformable characters,
   vertex group weight painting would be required.

2. **Preview-only animation**: The Option B mesh repositioning technique is applied
   per-frame at render time. It is not a real-time playable animation in Blender's
   viewport without the render script running.

3. **Shin visibility**: Since shins are separate rigid meshes from thighs, the
   shin_bounce keyframes provide visual suggestion of knee flex but no actual geometric
   bending at the joint.

4. **Both-characters render**: Aanya's data is appended via library load. If object
   names conflict, Blender will rename duplicates — handled by using `Aanya`-prefixed
   object names throughout.

---

## 6. File Inventory

```
blender/scripts/
  create_animations.py           # Creates IDLE + WALK actions in stage4 blend files
  render_animation_preview.py    # Renders 5 animation preview PNGs

blender/assets/characters/
  aarav/aarav_stage4.blend       # Working copy: AARAV_IDLE + AARAV_WALK (783,569 bytes)
  aanya/aanya_stage4.blend       # Working copy: AANYA_IDLE + AANYA_WALK (805,405 bytes)

output/stage4_1/previews/
  aarav_idle.png                 # 640x360, 169,061 bytes
  aarav_walk.png                 # 640x360, 167,696 bytes
  aanya_idle.png                 # 640x360, 176,854 bytes
  aanya_walk.png                 # 640x360, 176,339 bytes
  both_characters_animation.png  # 640x360, 170,224 bytes

tests/
  test_stage4_1_animations.py    # 13 tests (all passing)

reports/
  stage4_1_character_rigging_report.md         (this file)
  stage4_1_animation_validation_report.md
```
