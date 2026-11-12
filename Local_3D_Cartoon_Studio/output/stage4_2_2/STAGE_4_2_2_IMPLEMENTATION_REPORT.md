# Stage 4.2.2 Implementation Report

## Overview

Stage 4.2.2 extends the offset-corrected Option B mesh repositioning first introduced in Stage 4.2.1 to cover the head and neck bones. Stage 4.2.1 fixed arm and leg mesh displacement for all animated poses but excluded head and neck from the `_SAFE_BONES` set as a conservative measure — head mesh objects had not yet been tested with Option B at that time, and head nodding was therefore not visually reflected in rendered output.

Stage 4.2.2 confirms via probe (`probe_results.json`) that both head and neck mesh objects use `parent_type=OBJECT` (rigid parenting, not `BONE` parenting), making them directly compatible with the same offset-corrected approach used for arm and leg meshes. With this confirmation, `head` and `neck` are added to `_SAFE_BONES`, the `_BONE_TO_MESH` mapping is updated to associate Aanya's Hijab with the `head` bone, and the NOD action keyframe angles are increased to deliver clearly visible head movement. All 16 automated tests pass (15 passed, 1 skipped — `check_before_push.py` not present in this environment).

---

## Files Changed

### `blender/scripts/character_movement.py`

| Change | Detail |
|---|---|
| `_SAFE_BONES` expanded | `'head'` and `'neck'` added to the frozenset. Previously only arm and leg bones were included. |
| `_BONE_TO_MESH` `'head'` entry updated | Now maps to `['Head', 'Hijab']`. The `'Hijab'` suffix is silently skipped for Aarav (no `Aarav_Hijab` object exists); for Aanya it moves the hijab mesh to follow the head bone midpoint with the same offset correction as all other meshes. |
| Docstring updated | Safety rationale added in comment block above `_SAFE_BONES`, referencing `probe_results.json` confirmation of `parent_type=OBJECT` for head and neck meshes. |
| `apply_action_pose` docstring updated | Notes that head and neck are included from Stage 4.2.2 with the same offset-correction logic as arms/legs. |

A timestamped backup was created before modification:
`blender/scripts/character_movement.py.bak_20261112_103726`

### `blender/scripts/gesture_library.py`

| Change | Detail |
|---|---|
| NOD action keyframe angles increased | Frame 1: 0.0 rad (unchanged). Frame 4: raised from a sub-visible value to **0.5 rad (~29°)** — the peak nod. Frame 8: −0.1 rad (slight back-rebound past neutral). Frame 12: 0.3 rad (second nod, still clearly visible). Frame 16: 0.0 rad (return to neutral). The 0.5 rad peak is well above the test threshold of 0.4 rad. |
| Applies to both characters | The same angle values are used for `AARAV_NOD` and `AANYA_NOD`. |

A timestamped backup was created before modification:
`blender/scripts/gesture_library.py.bak_20261112_103726`

### `blender/scripts/render_stage422_previews.py` (new file)

Orchestrator script that runs outside Blender and launches `blender.exe` as subprocesses to produce 14 PNG previews. Key design points:

- Writes each inline Blender script to `.agents/tasks/stage422/` before execution.
- Imports `character_movement` functions (`compute_rest_offsets`, `apply_action_pose`, `restore_pose`, `setup_workbench`, `make_camera`).
- Single-character renders use a 50 mm lens at `(0, -4.5, 0.875)` looking at `(0, 0, 0.875)`.
- Combined renders use a 40 mm lens at `(0, -5.5, 0.875)` with Aarav at X = −0.6 and Aanya at X = +0.6.
- Applies the established 180° Z-rotation correction for Aanya in all single-character and combined renders.
- Safety guard refuses to write into `output/stage4_2_1/previews/`, `output/stage4_2/previews/`, or `output/stage4_1/previews/`.
- Prints `RENDER_STAGE422_PREVIEW_OK` when all 14 files exceed 20 KB; prints `RENDER_STAGE422_PREVIEW_WARNINGS` otherwise.

### `tests/test_stage4_2_2_transform_hierarchy.py` (new file)

16-test suite — see the Test Report for details.

---

## Architecture Decision

### Why offset-corrected Option B is safe for head and neck

The core question for this stage was whether applying Option B to head and neck meshes would cause detachment or double-transformation artefacts. The answer depends entirely on the parenting mode of those mesh objects in the Blender file.

**Probe result:** `probe_results.json` confirmed that `Aarav_Head`, `Aanya_Head`, `Aarav_Neck`, and `Aanya_Neck` all have `parent_type == 'OBJECT'` (rigid object parenting, not bone parenting). This is the same parenting mode as the arm and leg mesh objects that have been working correctly since Stage 4.2.1.

With `parent_type=OBJECT`:
- The mesh object does **not** inherit bone transforms from the armature automatically.
- Moving the mesh object location directly is the only way to reflect bone movement.
- The offset correction `new_pos = new_bone_midpoint + rest_offset` correctly repositions the mesh relative to the evaluated bone midpoint, preserving the original spatial relationship without any double-transformation risk.

The head and neck therefore receive exactly the same treatment as upper arms, forearms, thighs, and shins — all of which passed without detachment throughout Stage 4.2.1.

**Aanya Hijab:** Because the Hijab mesh is parented to the head bone's object (or is itself a free object that moves with the head), it is mapped to the `head` bone entry in `_BONE_TO_MESH`. The offset correction applies identically. For Aarav, `bpy.data.objects.get('Aarav_Hijab')` returns `None` and the entry is silently skipped — no special-casing required.

---

## Test Results

Ran with Python 3.11.9 / pytest 8.3.5 on Windows 10.

### Stage 4.2.2 suite — `test_stage4_2_2_transform_hierarchy.py`

| Result | Count |
|---|---|
| Passed | 15 |
| Skipped | 1 (`test_check_before_push_syntax` — `check_before_push.py` not present) |
| Failed | 0 |
| **Total** | **16** |

### Stage 4.2.1 regression suite — `test_stage4_2_1_reliability.py`

| Result | Count |
|---|---|
| Passed | 12 |
| Failed | 0 |
| **Total** | **12** |

---

## Known Limitations

- **Spine and chest meshes remain stationary.** `spine`, `chest`, and `shoulder_L/R` bones are not in `_SAFE_BONES`. These bones use a more complex parenting structure and moving them without further investigation risks detachment of torso geometry. Excluding them does not affect NOD, WAVE, POINT, or WALK animations because those gestures do not require visible torso translation.
- **Nod sequence previews are single-frame.** `aarav_nod_sequence.png` and `aanya_nod_sequence.png` show frame 4 (peak nod) rather than a true contact sheet of multiple frames. A multi-frame contact sheet could be added in a future stage if required.
- **`check_before_push.py` not present.** `test_check_before_push_syntax` is skipped on this machine. The syntax check would need `check_before_push.py` to exist at the repository root.
- **Blender-dependent tests require Blender 4.4.3.** Tests 6 and 7 (`test_aarav_nod_action_head_rotation`, `test_aanya_nod_action_head_rotation`) are skipped if `blender.exe` is not found at the configured path.

---

## Acceptance Criteria Status

| Criterion | Status |
|---|---|
| Head nodding is visually functional (`AARAV_NOD`, `AANYA_NOD`) | ✅ Done — `head` added to `_SAFE_BONES`; NOD peak angle 0.5 rad (~29°) |
| Hijab follows Aanya's head movement | ✅ Done — `_BONE_TO_MESH['head']` now includes `'Hijab'` |
| Original `aarav.blend` and `aanya.blend` unchanged | ✅ Verified — file sizes match (774392 and 796228 bytes respectively) |
| Working copies (`aarav_stage4.blend`, `aanya_stage4.blend`) exist | ✅ Verified |
| Existing gestures (WAVE, POINT, WALK, GREETING) not regressed | ✅ Verified via Stage 4.2.1 regression suite (12/12 passed) |
| Aanya 180° orientation correction preserved | ✅ Applied in all single-character and combined renders |
| Aarav +Y-facing geometry preserved | ✅ No changes to Aarav mesh orientation |
| 14 PNG previews generated at 640×360 | ✅ All 14 present and > 20 KB |
| All previews are valid PNG files | ✅ PNG magic bytes confirmed |
| All previews > 20 KB | ✅ Confirmed |
| `aarav_nod.png` visibly differs from `aarav_idle.png` | ✅ SHA-256 differs; pixel diff ≥ 2% |
| `aanya_nod.png` visibly differs from `aanya_idle.png` | ✅ SHA-256 differs; pixel diff ≥ 2% |
| Stage 4.2.1 previews not overwritten | ✅ Safety guard in `render_stage422_previews.py` |
| `_SAFE_BONES` includes `'head'` and `'neck'` | ✅ Confirmed by test 5 |
| NOD head X rotation at frame 4 ≥ 0.4 rad | ✅ 0.5 rad (both characters) |
| All 16 new tests pass (or skip for environment reason) | ✅ 15 passed, 1 skipped |
