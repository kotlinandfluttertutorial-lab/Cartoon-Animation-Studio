# Stage 4.2.2 Test Report

Test run: Python 3.11.9 / pytest 8.3.5 / Windows 10

---

## New Tests — `tests/test_stage4_2_2_transform_hierarchy.py`

16 tests total.

| # | Test name | Description | Result |
|---|---|---|---|
| 1 | `test_aarav_original_unchanged` | `aarav.blend` is exactly 774 392 bytes (original asset unchanged) | PASS |
| 2 | `test_aanya_original_unchanged` | `aanya.blend` is exactly 796 228 bytes (original asset unchanged) | PASS |
| 3 | `test_aarav_stage4_exists` | `aarav_stage4.blend` working copy exists | PASS |
| 4 | `test_aanya_stage4_exists` | `aanya_stage4.blend` working copy exists | PASS |
| 5 | `test_safe_bones_includes_head` | `_SAFE_BONES` frozenset in `character_movement.py` contains both `'head'` and `'neck'` | PASS |
| 6 | `test_aarav_nod_action_head_rotation` | `AARAV_NOD` action head X rotation at frame 4 is ≥ 0.4 rad (actual: 0.5 rad) | PASS |
| 7 | `test_aanya_nod_action_head_rotation` | `AANYA_NOD` action head X rotation at frame 4 is ≥ 0.4 rad (actual: 0.5 rad) | PASS |
| 8 | `test_all_14_previews_exist` | All 14 PNG files are present in `output/stage4_2_2/previews/` | PASS |
| 9 | `test_all_previews_valid_png` | All 14 preview PNGs have valid PNG magic bytes (`\x89PNG\r\n\x1a\n`) | PASS |
| 10 | `test_all_previews_gt_20kb` | All 14 preview PNGs exceed 20 480 bytes (20 KB) | PASS |
| 11 | `test_aarav_nod_differs_from_idle` | SHA-256 of `aarav_nod.png` ≠ SHA-256 of `aarav_idle.png` (head visibly moved) | PASS |
| 12 | `test_aanya_nod_differs_from_idle` | SHA-256 of `aanya_nod.png` ≠ SHA-256 of `aanya_idle.png` (head visibly moved) | PASS |
| 13 | `test_aarav_nod_pixel_diff` | `aarav_nod.png` vs `aarav_idle.png` differ by ≥ 2% of pixels (Pillow pixel comparison) | PASS |
| 14 | `test_aanya_nod_pixel_diff` | `aanya_nod.png` vs `aanya_idle.png` differ by ≥ 2% of pixels (Pillow pixel comparison) | PASS |
| 15 | `test_regression_stage421` | `tests/test_stage4_2_1_reliability.py` exits 0 — no regressions introduced | PASS |
| 16 | `test_check_before_push_syntax` | `check_before_push.py --syntax` exits 0 (skipped: script not present at repo root) | SKIP |

**Suite result: 15 passed, 1 skipped, 0 failed**

---

## Regression Tests — `tests/test_stage4_2_1_reliability.py`

12 tests total. All pass.

| # | Test name | Description | Result |
|---|---|---|---|
| 1 | `TestFileIntegrity::test_aarav_orig_file_unchanged` | `aarav.blend` file size matches expected value | PASS |
| 2 | `TestFileIntegrity::test_aanya_orig_file_unchanged` | `aanya.blend` file size matches expected value | PASS |
| 3 | `TestCharacterMovementAPI::test_character_movement_has_compute_rest_offsets` | `character_movement.py` exports `compute_rest_offsets` | PASS |
| 4 | `TestCharacterMovementAPI::test_character_movement_has_safe_bones` | `character_movement.py` exports `_SAFE_BONES` | PASS |
| 5 | `TestPreviewFiles::test_all_12_previews_exist` | All 12 Stage 4.2.1 PNG previews are present | PASS |
| 6 | `TestPreviewFiles::test_all_12_previews_are_valid_pngs` | All 12 Stage 4.2.1 previews have valid PNG headers | PASS |
| 7 | `TestPreviewFiles::test_all_12_previews_gt_20kb` | All 12 Stage 4.2.1 previews exceed 20 KB | PASS |
| 8 | `TestGestureActions::test_aarav_gesture_actions_present` | Aarav gesture actions are present in working blend file | PASS |
| 9 | `TestGestureActions::test_aanya_gesture_actions_present` | Aanya gesture actions are present in working blend file | PASS |
| 10 | `TestGestureActions::test_aarav_regression_actions` | Aarav regression actions (IDLE, WALK, etc.) are present | PASS |
| 11 | `TestGestureActions::test_aanya_regression_actions` | Aanya regression actions (IDLE, WALK, etc.) are present | PASS |
| 12 | `TestRenderScript::test_render_stage421_script_exists` | `render_stage421_previews.py` script file exists | PASS |

**Suite result: 12 passed, 0 failed**

---

## Total Counts

| Suite | Passed | Skipped | Failed | Total |
|---|---|---|---|---|
| `test_stage4_2_2_transform_hierarchy.py` | 15 | 1 | 0 | 16 |
| `test_stage4_2_1_reliability.py` (regression) | 12 | 0 | 0 | 12 |
| **Combined** | **27** | **1** | **0** | **28** |

No existing tests were weakened or removed. The single skip (`test_check_before_push_syntax`) is a genuine environment limitation — `check_before_push.py` is not present at the repository root on this machine — and is not a test failure.
