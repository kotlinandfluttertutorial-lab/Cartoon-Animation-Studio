# Stage 4.2 — Interaction Validation Report

**Project:** Local 3D Cartoon Animation Studio  
**Stage:** 4.2 — Character Movement, Interaction & Gesture System  
**Date:** 2026-11-11

---

## Aanya Orientation Investigation

### Probe Results

A Blender subprocess probed `rotation_euler` and `location` of all parentless
objects in both blend files after Stage 4.2 gestures were applied.

**Aarav_Armature (aarav_stage4.blend):**
```
rotation_euler = (0.0, 0.0, 0.0)
location       = (0.0, 0.0, 0.0)
```

**Aanya_Armature (aanya_stage4.blend):**
```
rotation_euler = (0.0, 0.0, 0.0)
location       = (0.0, 0.0, 0.0)
```

### Finding

Both armatures have zero rotation at their object level.  Aanya does **not**
have a Z-axis offset relative to Aarav.  Both characters face +Y at rest.

The orientation issues observed in Stage 4.1 combined renders were due to
camera placement (camera was at -Y but characters face +Y), not an armature
rotation mismatch.

### Fix Applied

`render_stage42_previews.py` includes `fix_aanya_orientation()` which:
1. Reads `Aanya_Armature.rotation_euler[2]` after appending Aanya into a
   combined scene.
2. If non-zero (> 1e-4 rad), counter-rotates all Aanya parentless objects by
   `-rotation_euler[2]` on Z.
3. During Stage 4.2 renders, the probe found 0.0 rad — no correction was needed.
4. The function remains in place as a defensive guard for future blend file
   variants.

---

## Camera Setup

### Single Character Camera
- Position: `(0, 4.5, 0.875)` — camera at +Y, characters face +Y (consistent
  with Stage 4.1 front-view convention)
- Target: `(0, 0, 0.875)` — Z center at half character height (1.75 / 2)
- Lens: 50 mm
- Provides feet-to-head coverage at 640×360 with comfortable margins

### Two-Character Camera
- Position: `(0, 6.0, 0.875)` — pulled back for wider field of view
- Target: `(0, 0, 0.875)`
- Lens: 40 mm — slightly wider FOV to fit both characters
- Aarav at X = -0.5, Aanya at X = +0.5 (tighter than Stage 4.1 ±0.8 spacing)

---

## Combined Scene Setup

1. Load `aarav_stage4.blend`.
2. `bpy.data.libraries.load(AANYA_BLEND, link=False)` — appends all Aanya objects.
3. Link any Aanya objects not yet in `scene.collection.objects`.
4. Call `fix_aanya_orientation()` before offsetting X positions.
5. Set Aarav parentless objects to X = -0.5.
6. Set Aanya parentless objects to X = +0.5.
7. Apply Option B poses for both characters independently.
8. Render and restore.

---

## 8 Preview Renders

| # | Filename | Size (bytes) | Resolution | Visual Description |
|---|---|---|---|---|
| 1 | `aarav_wave.png` | 164,291 | 640×360 | Aarav with right arm raised at WAVE action frame 10 — arm extended upward with hand tilted |
| 2 | `aanya_wave.png` | 164,664 | 640×360 | Aanya mirroring wave pose at frame 10 |
| 3 | `aarav_point.png` | 163,862 | 640×360 | Aarav pointing forward with right arm extended at POINT action frame 8 |
| 4 | `aanya_nod.png` | 165,353 | 640×360 | Aanya with head tilted forward at NOD action frame 4 |
| 5 | `greeting_interaction.png` | 165,861 | 640×360 | Both characters side-by-side, both beginning GREETING arm-raise at frame 6 |
| 6 | `walk_together.png` | 162,689 | 640×360 | Both characters in improved WALK stride frame 1 with wider thigh swing |
| 7 | `both_facing_camera.png` | 169,237 | 640×360 | Both characters in IDLE frame 12 facing the +Y camera |
| 8 | `pointing_interaction.png` | 162,468 | 640×360 | Aarav pointing (POINT fr8) while Aanya nods (NOD fr4) — interaction scene |

All 8 renders: 640×360 PNG, >20 KB, valid PNG signature (0x89504E470D0A1A0A).

---

## Known Limitations

- Option B repositions mesh objects to bone midpoints only for keyed bones.
  Unkeyed bones (e.g. fingers if present) retain their rest-pose positions.
- Hip-sway bone (`hips`) drives no mesh objects in `_BONE_TO_MESH` (empty list)
  since the character rigs use a flat bone hierarchy; the sway is encoded in
  thigh positions.
- Foot contact is approximated by shin/thigh keyframes rather than IK — some
  foot sliding may be visible at extended stride lengths.
