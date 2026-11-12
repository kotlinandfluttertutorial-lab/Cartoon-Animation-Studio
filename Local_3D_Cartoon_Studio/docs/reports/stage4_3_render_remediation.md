# Stage 4.3 facial render remediation

## Root causes

- The speech renderer and the earlier one-off viseme preview script replaced the mouth's authored local scale of (0.065, 0.015, 0.018) with viseme factors. Both mouth objects are eight-vertex boxes. Their evaluated rest dimensions were 0.130 x 0.030 x 0.036 Blender units. Applying OPEN as an absolute scale made each box 2.6 x 2.0 x 2.8 units, larger than the roughly 1.7-unit characters. The pink surfaces came from the materials on `Aarav_Mouth` and `Aanya_Mouth`. The boxes blocked the camera's sightline from its original 4.5-unit distance.
- The inspected facial meshes were object-parented to their character's armature, with identity parent-inverse matrices and unit-scale armature transforms. Their local rest dimensions matched the evaluated world dimensions. The oversizing came from scale assignment, independent of the camera and parenting.
- All three old render paths used a +Y camera aimed at Z = 0.875. In the unrotated solo assets, Aarav's nose sits on +Y and Aanya's on -Y. The camera saw the back of Aanya's head. This matches Stage 4.2.3's separate camera directions for solo renders.
- Aarav's small mouth box sat partly behind the curved head and could only produce a flattened bar. On Aanya's front side, the rear hijab panel had been placed on -Y and the cap extended down toward the brows. Aanya's iris and sclera surfaces also met at the same front depth.

## Fixes

- `blender/scripts/facial_preview.py` shares camera and render setup, applies viseme multipliers to the current mouth scale, and fits temporary mouth silhouettes to the head surface in world space. It provides a curved smile, a round surprised mouth, and visibly different speech shapes.
- `blender/scripts/apply_lipsync.py` uses the shared path for each frame and scales both irises and eye whites during blinks. `blender/scripts/apply_expression.py` uses the existing expression library and the same fitted mouth geometry.
- The orthographic camera frames each native-facing character from the correct side. The preview scene places Aanya's rear scarf panel behind her head, opens the cap around the face, and seats the facial features. The original mouth data is restored after each render. No character asset was saved.

## Before and after

All six PNGs in `output/stage4_3/previews` were regenerated at 640 x 360 and inspected at their original resolution. Both heads and bodies fit inside the frame, both sets of eyes and eyebrows are visible, and Aanya's hijab is intact. The review was performed by the assistant.

| Preview | Before | After |
| --- | --- | --- |
| aanya_speaking_1.png | Large pink panel filled the image | Front view with a wide, open mouth |
| aanya_speaking_2.png | Pink panel obscured the head | Front view with a small closed-lip MBP shape |
| aanya_surprised.png | Back view hid the face | Raised brows, wide eyes, and a round open mouth |
| aarav_happy.png | Flat, faint mouth and tight framing | Curved smile with the full body in frame |
| aarav_speaking_1.png | Mouth mesh filled the image | Full body with an open oval mouth |
| aarav_speaking_2.png | Mouth mesh obscured the upper body | Full body with a wide, shallow EI shape |

To reproduce the speech previews, run `apply_lipsync.py` with a two-frame JSON and the corresponding `*_stage4.blend`. Set `total_frames` to 2 and use `"frames": {"1": "OPEN", "2": "EI"}` for Aarav or `"frames": {"1": "OPEN", "2": "MBP"}` for Aanya. The two numbered output frames map to speaking previews 1 and 2. For the expressions, run `apply_expression.py` with the same blends and use `Aarav happy` or `Aanya surprised` with the requested output path.

## Verification

| Check | Result |
| --- | --- |
| Stage 4.3 dialogue, expression, and lip-sync tests | 34 passed |
| Stage 4.2.3 regression set | 61 passed, including 16 Stage 4.2.2 transform tests and 13 Stage 4.1 animation tests |
| Blender runner, character rig, and integration suites | 16 passed |
| Full `check_before_push.py` | Exit 0, 14 checks passed, 0 failures, 2 warnings, 0 skips. The full suite inside the check passed all 160 tests. |

The pre-push warnings covered the dirty working tree and tracked backup files. The tests ran in a disposable copy so generation tests could exercise their write paths. SHA-256 hashes matched for all 79 character asset files in the original workspace before and after testing.

A Blender geometry probe exercised all seven visemes and six expressions on each character. It verified camera side, body bounds inside the frame, mouth widths from 0.0754 to 0.182 Blender units, and restoration of the original mouth mesh and transform.

## Remaining limitations

The mouth poses are stylized surface silhouettes for the solo Stage 4 assets. They approximate phonemes without a deforming jaw, tongue, or teeth. Continuous playback and audio timing are outside this still-image review.
