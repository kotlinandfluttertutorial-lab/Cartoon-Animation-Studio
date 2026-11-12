# Stage 4.3 Code Review — Dialogue, Lip-Sync and Expression System
**Date:** 2026-11-12  
**Branch:** feature/stage-4-3-dialogue-lipsync  
**Reviewer:** Automated review pass  
**Verdict:** APPROVED

---

## Acceptance Criteria Verification

| # | Criterion | Result |
|---|---|---|
| 1 | All 7 `studio/dialogue/` files exist (`__init__.py` + 6 modules) | PASS — all 7 confirmed on disk |
| 2 | `test_stage4_3_dialogue.py` ≥ 10 tests passed | PASS — 13/13 |
| 3 | `test_stage4_3_lipsync.py` ≥ 8 tests passed | PASS — 11/11 |
| 4 | `test_stage4_3_expressions.py` ≥ 8 tests passed | PASS — 10/10 |
| 5 | All 61 Stage 4.2.x regression tests pass | PASS — 61/61 |
| 6 | All 6 preview PNGs at 640×360 > 20 KB | PASS — all 6 present, 166 KB–228 KB |
| 7 | `check_before_push.py --fast`: 0 FAIL | PASS — 0 FAIL, 13 PASS |
| 8 | No `shell=True` in any subprocess call | PASS — no match in diff |
| 9 | No modifications to blend files or Stage 4.2.x scripts | PASS — diff contains only new files |
| 10 | `LipsyncData` save/load roundtrip verified | PASS — test_05 / test_06 cover it |
| 11 | Branch pushed to `origin/feature/stage-4-3-dialogue-lipsync` | PASS — confirmed via `git branch -vv` |

---

## Detailed Findings

### 1. Phoneme → Viseme Mapping (`phoneme_mapper.py`)

The 7-viseme ARPABET table is correct:
- **REST** ← SIL, SP
- **MBP** ← M, B, P (bilabials)
- **FV** ← F, V (labiodentals)
- **TD** ← T, D, N, L, S, Z, TH, DH, plus velars K, G, NG, CH, JH, SH, ZH mapped to TD as an approximation. HH → OPEN (open glottal) is reasonable.
- **WQ** ← W, R, OW, UW, UH, OY, AW (rounded vowels and glides)
- **OPEN** ← AA, AH, AO, AE
- **EI** ← EH, IH, IY, AY, EY, ER, Y

The commit message mentions the mapping as `REST MBP FV TD WQ OPEN EI`. The implementation matches. The module docstring's viseme table omits a few entries (EY, ER, Y, UH, etc.) but those are present in `_ARPABET_TO_VISEME` — the table in the docstring is non-normative. The rule-based fallback provides a valid default (`"AH"`) for all-unknown input.

`text_to_viseme_sequence` correctly places REST at frame 1 and frame `total_frames`, distributes interior visemes over `[2, total_frames-1]`, and deduplicates colliding frames.

### 2. Mouth Transforms (`mouth_shapes.py`)

`VISEME_MOUTH_TRANSFORMS` is internally consistent:
- REST: identity scale, no offset — correct baseline.
- MBP: narrow X/Z (lips together) — correct.
- FV: intermediate narrow — correct.
- TD: moderate scale reduction with slight downward Z — appropriate for tongue-tip approximation.
- WQ: narrow X, tall Z with slight downward Z — rounded lips represented correctly.
- OPEN: wider X, taller Z, downward offset — open jaw, correct.
- EI: wide X, compressed Z — spread-lips smile, correct.

All `z_offset` values are small relative to character scale (~0.005–0.015), consistent with mesh-object transforms seen in prior stages.

### 3. `LipsyncData` JSON Serialization / Deserialization

`save_lipsync()` serialises int frame keys to strings (required by JSON spec). `load_lipsync()` converts them back to `int` explicitly. `LipsyncData.__post_init__` also handles string-key coercion if the dataclass is constructed directly from raw JSON. The roundtrip is doubly safe.

Confirmed with on-disk sample: `aarav_hello_aany.json` has string keys `"1"`, `"2"` etc. and all values are valid viseme names.

### 4. Blender Script Safety (`apply_lipsync.py`, `apply_expression.py`)

**No blend files are opened for write.** Both scripts run in `--background` mode; they read the blend, render, then exit. No `bpy.ops.wm.save_mainfile()` or equivalent is called.

**Mouth restore after each frame:** `apply_lipsync.py` calls `restore_mouth()` after every `bpy.ops.render.render(write_still=True)` call (line inside the render loop, unconditional). The eyes are also restored via `restore_eyes()` after the loop. This satisfies the requirement.

**Expression restore after render:** `apply_expression.py` explicitly restores all modified objects in a `saved_state` loop after the render call completes.

**No `shell=True`:** Confirmed — `Select-String` found only the comment in `dialogue_sequencer.py` docstring, not any actual `subprocess.run` call.

**Subprocess argument lists:** Both `dialogue_sequencer.py` (Piper TTS, ffprobe) and `conversation_scene.py` (Blender) build their `cmd` as plain Python lists. No string concatenation, no shell metacharacter risk.

### 5. No Modifications to Existing Assets or Scripts

`git diff origin/develop...HEAD --name-only` lists only new files. No changes to:
- `aarav.blend` (774,392 bytes, confirmed on disk) ✓
- `aanya.blend` (796,228 bytes, confirmed on disk) ✓
- `aarav_stage4.blend` / `aanya_stage4.blend` ✓
- Any `test_stage4_2*.py` or Stage 4.2.x animation scripts ✓
- `check_before_push.py` ✓

### 6. Test Coverage — Edge Cases

| Edge case | Covered by |
|---|---|
| Empty text | `test_13_empty_text_handled_gracefully` (dialogue), `text_to_viseme_sequence("")` returns `[(1,"REST"),(N,"REST")]` |
| Single word | exercised indirectly via several tests |
| Long sentence (all 7 visemes) | `test_03_all_seven_visemes_in_long_text` |
| `include_blinks=False` | `test_08_no_blinks_when_disabled` |
| Non-default fps | `test_09_fps_parameter_respected` |
| Missing JSON file | `test_10_missing_file_raises` |
| `get_viseme` for unlisted frame → REST | `test_07_get_viseme_defaults_to_rest` |
| Frame 1 always REST | `test_12_sequence_frame_one_is_rest`, `test_02_frame_one_is_rest` |

Edge case coverage is adequate for the stage.

### 7. Notes (Non-Blocking)

- `apply_lipsync.py` mirrors `VISEME_MOUTH_TRANSFORMS` and `BLINK_*` constants inline rather than importing `mouth_shapes.py`. This is an intentional design choice (Blender scripts can't easily import from the studio package without `sys.path` manipulation). The values are identical to the Python module; no discrepancy found.
- The `aarav_hello_aany.json` sample has `blink_frames: []` because the clip is 60 frames (< 96 threshold). This is correct — no blink fires before frame 96 in a 60-frame clip.
- Piper TTS fallback (zero-byte WAV + text-length estimate) is documented as a known limitation; this is intentional and recorded.

---

## Summary

All 11 acceptance criteria are met. No correctness, security, or data failures were found. No pre-existing issues were introduced. The implementation is clean and consistent.
