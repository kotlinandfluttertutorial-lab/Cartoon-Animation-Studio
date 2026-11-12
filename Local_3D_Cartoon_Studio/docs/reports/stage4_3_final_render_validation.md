# Stage 4.3 final render validation

Validated on 2026-11-12 in Local 3D Cartoon Animation Studio.

## Visual inspection

The assistant opened all six current PNGs at their native 640 x 360 resolution. Each shows a front-facing character with the full head, hands, body, and feet inside the frame. The eyes, eyebrows, nose, and mouth are visible. The mouths sit on the face and all six sightlines are clear. Aanya's cap and side panels are present and clear of her eyes and mouth in all three frames.

| Preview | Before remediation | Current visual result |
| --- | --- | --- |
| [aanya_speaking_1.png](../../output/stage4_3/previews/aanya_speaking_1.png) | A pink surface filled most of the frame | **Pass.** Wide, dark OPEN oval below the nose. |
| [aanya_speaking_2.png](../../output/stage4_3/previews/aanya_speaking_2.png) | A pink panel obscured the head | **Pass.** Short, closed MBP line clearly differs from OPEN. |
| [aanya_surprised.png](../../output/stage4_3/previews/aanya_surprised.png) | Rear view concealed the face | **Pass.** Raised brows, tall eye whites with visible irises, and a round open mouth read as surprise. |
| [aarav_happy.png](../../output/stage4_3/previews/aarav_happy.png) | Faint, flat mouth and tight framing | **Pass.** The mouth curves upward at the corners and the full character is framed. |
| [aarav_speaking_1.png](../../output/stage4_3/previews/aarav_speaking_1.png) | An enlarged mouth surface filled the frame | **Pass.** Open oval below the nose with a clear face and body. |
| [aarav_speaking_2.png](../../output/stage4_3/previews/aarav_speaking_2.png) | An enlarged mouth surface obscured the upper body | **Pass.** Wide, shallow EI mouth clearly differs from OPEN. |

The [before and after contact sheet](C:/Users/admin/.codex/visualizations/2026/11/12/01a1d0dd-3343-7991-9905-fd0ad59f0803/stage43-before-after.png) pairs the defective images preserved before remediation with the six current PNGs. A pixel comparison of each speaking pair also confined the changes to the head region. The visual pass required no additional fixes or rerenders.

## Root causes and existing fixes

- The previous speech renderer assigned viseme factors directly to the local scale of the armature-parented `Aarav_Mouth` and `Aanya_Mouth` meshes. Their authored dimensions were 0.130 x 0.030 x 0.036 Blender units. OPEN expanded the boxes to 2.6 x 2.0 x 2.8 units. The shared preview code now multiplies the authored scale, fits temporary mouth geometry against the head surface, and restores the mouth state after rendering.
- A +Y camera worked for Aarav and showed Aanya from behind. The shared setup uses the native Stage 4.2.3 solo orientations, +Y for Aarav and -Y for Aanya, and uses orthographic framing.
- The mouth boxes lacked readable expression silhouettes. Aanya's rear scarf panel also occupied the facial side, and her irises shared the front depth of the eye whites. The remediation added shaped mouth profiles and adjusted the scarf and facial feature depths in memory.

The implementation and render reproduction steps are in the [remediation report](stage4_3_render_remediation.md).

## Automated verification

| Suite | Passed |
| --- | ---: |
| Stage 4.3 dialogue, expressions, and lip-sync | 34 |
| Stage 4.2.2 transform hierarchy, including the Stage 4.2.3 orientation regressions | 16 |
| Stage 4.2.1 reliability | 12 |
| Stage 4.2 movement | 20 |
| Stage 4.1 animations | 13 |
| Blender runner, character rig, and integration | 16 |
| Full suite | 160 |

The full `python check_before_push.py` run exited 0 with 14 checks passed, 0 failures, 2 warnings, and 0 skips. The warnings concerned uncommitted changes and tracked backup files. The full pytest suite had zero failures, errors, or skips. [Pre-push log](C:/Users/admin/.codex/visualizations/2026/11/12/01a1d0dd-3343-7991-9905-fd0ad59f0803/final-validation-pre-push.log)

The checks ran on a disposable copy of the current working files so asset generation tests could write there. SHA-256 hashes matched for all 79 character asset files in the original checkout before and after validation. A Blender geometry check verified camera direction, framing, mouth dimensions, and mouth-state restoration for all seven visemes and six expressions on both characters.

## Remaining limitations

These are solo, full-body stills. The facial poses use stylized mouth silhouettes. The MBP line is intentionally small, and the raised brows in Aanya's surprise pose sit close to the cap. The review covers pose readability and framing. Continuous playback and audio timing are outside its scope. This is an assistant visual review.

## Git status

- Branch `feature/stage-4-3-dialogue-lipsync`
- HEAD `07b30af7f83cd835dba1bdd4588400cdcce4e42a`, one commit ahead of the local remote-tracking ref at `32e7cd1fbadba6c4ffd04e26f8b428b408eb2462`
- The shared render helper and remediation report were already staged. The two render entry points and six corrected PNGs were unstaged, alongside unrelated local changes. This validation report is uncommitted.
