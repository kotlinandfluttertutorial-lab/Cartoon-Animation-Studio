# Stage 4.2 — Gesture Library Report

**Project:** Local 3D Cartoon Animation Studio  
**Stage:** 4.2 — Character Movement, Interaction & Gesture System  
**Script:** `blender/scripts/gesture_library.py`  
**Date:** 2026-11-11

---

## Overview

`gesture_library.py` runs inside Blender background mode and creates four gesture
actions plus an improved WALK action for each character.  All actions use
`use_fake_user = True` to ensure they persist across file load/save without
needing an active NLA assignment.

---

## Actions Created per Character

### `<NAME>_WAVE` (24 frames)

| Frame | Bone | Channel | Value |
|---|---|---|---|
| 1 | `upper_arm_R` | X | 0.0 |
| 6 | `upper_arm_R` | X | -1.4 |
| 6 | `upper_arm_R` | Z | 0.3 |
| 10 | `hand_R` | Z | +0.3 |
| 14 | `hand_R` | Z | -0.3 |
| 18 | `upper_arm_R` | X | -1.4 |
| 24 | `upper_arm_R` | X | 0.0 (rest) |
| 24 | `hand_R` | Z | 0.0 (rest) |

**Bones keyed:** `upper_arm_R` (X, Z), `hand_R` (Z)  
**Total keyframe points:** 13  
**Use fake user:** True

---

### `<NAME>_POINT` (20 frames)

| Frame | Bone | Channel | Value |
|---|---|---|---|
| 1 | `upper_arm_R` | X | 0.0 |
| 6 | `upper_arm_R` | X | -0.8 |
| 6 | `upper_arm_R` | Z | -0.2 |
| 8 | `forearm_R` | X | -0.3 (elbow bend) |
| 15 | `upper_arm_R` | hold | -0.8 |
| 15 | `forearm_R` | hold | -0.3 |
| 20 | all | — | 0.0 (rest) |

**Bones keyed:** `upper_arm_R` (X, Z), `forearm_R` (X)  
**Total keyframe points:** 14  
**Use fake user:** True

---

### `<NAME>_NOD` (16 frames)

| Frame | Bone | Channel | Value |
|---|---|---|---|
| 1 | `head` | X | 0.0 (neutral) |
| 4 | `head` | X | 0.3 (nod down) |
| 8 | `head` | X | -0.1 (past neutral, slight back-tilt) |
| 12 | `head` | X | 0.2 (nod down again) |
| 16 | `head` | X | 0.0 (neutral) |

**Bones keyed:** `head` (X)  
**Total keyframe points:** 5  
**Use fake user:** True

---

### `<NAME>_GREETING` (48 frames)

Composite gesture combining wave (frames 1–24) and idle breathing (frames 24–48).

| Frames | Content |
|---|---|
| 1–6 | `upper_arm_R` X rises 0 → -1.4 (arm raises) |
| 6–18 | Wave: `hand_R` Z alternates +0.3 (fr 10) → -0.3 (fr 14) |
| 18–24 | `upper_arm_R` X returns -1.4 → 0 (arm lowers) |
| 24–48 | Idle breathing: `spine` Y peaks +0.03 at fr 36; `head` Z peaks +0.02 at fr 36 |

**Bones keyed:** `upper_arm_R` (X, Z), `hand_R` (Z), `spine` (Y), `head` (Z)  
**Total keyframe points:** 24  
**Use fake user:** True

---

### `<NAME>_WALK` (36 frames) — Improved (Fix 3)

Recreated with wider thigh swing, hip sway, and spine counter-rotation.

| Bone | Channel | Keyframes |
|---|---|---|
| `thigh_L` | X | ±0.5 at fr 1/18 (wider than original ±0.4) |
| `thigh_R` | X | ±0.5 at fr 1/18 |
| `upper_arm_L` | X | ±0.3 (opposing swing, unchanged) |
| `upper_arm_R` | X | ±0.3 (unchanged) |
| `shin_L` | X | -0.2/+0.1 (natural knee bend, unchanged) |
| `shin_R` | X | +0.1/-0.2 (unchanged) |
| `hips` | Z | ±0.1 hip sway (new Fix 3) |
| `spine` | Y | ±0.02 counter-rotation, out of phase (new Fix 3) |

**Bones keyed:** `thigh_L/R`, `upper_arm_L/R`, `shin_L/R`, `hips`, `spine`  
**Total keyframe points:** 40  
**Use fake user:** True  
**Improvements over Stage 4.1:** wider thigh swing (+25%), hip sway, spine counter-rotation

---

## Walking Improvements Summary (Fix 3)

| Parameter | Stage 4.1 | Stage 4.2 |
|---|---|---|
| Thigh swing | ±0.4 rad | ±0.5 rad (+25%) |
| Hip sway | None | ±0.1 rad Z on `hips` bone |
| Spine counter-rotation | None | ±0.02 rad Y, out of phase |
| Arm swing | ±0.3 rad (unchanged) | ±0.3 rad |
| Shin bend | ±0.1–0.2 rad (unchanged) | ±0.1–0.2 rad |

---

## Script Usage

```
blender --background <blend_file> --python gesture_library.py -- <blend_file> <character_name>
```

Success output: `GESTURES_CREATED_OK`

Script is idempotent: running twice replaces (removes and recreates) all actions
with the same names.  Uses the same `get_or_create_action()` helper as
`create_animations.py`.
