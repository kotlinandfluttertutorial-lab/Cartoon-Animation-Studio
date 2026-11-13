# Stage 13 visual review

The user approved Stage 12 animation and the independent Stage 13 camera and lighting studies. The cinematic sequence requires its own visual and audio review.

## Visual findings

I inspected 19 stills at native resolution and two contact sheets. I decoded all nine movement clips and visually inspected six ordered decoded frames per clip. Real-time playback review remains open.

- Establishing uses the path as the main line into the garden. Full-body Aarav and the walking and side-tracking views show heads, hands and feet. The medium two-shot has clear separation and room for both faces and hands. The conversation shot establishes coverage with stationary poses.
- Aanya's close-up keeps her face and hijab readable. Aarav's extreme close-up intentionally crops the hair while keeping his eyes, brows and mouth in frame. The earlier shoulder shot shows Aanya's back. The existing revision correctly uses Aarav as the cropped foreground figure and gives Aanya a clear face.
- Push-in and pull-back change subject size gradually. Pan and tilt stay on the garden. Track, follow, reveal and reposition show gradual changes in composition. Static holds the camera. Sampled frames show clear subjects with no abrupt reframing or visible obstruction. The follow and reveal clips use stationary cast, and both characters remain visible during the reveal.
- Daylight keeps both faces, skin tones, clothing and the hijab readable. Conversation is balanced for dialogue. Afternoon is softer, golden hour has a peach sky and deeper shade, morning darkens faces most, and close-up is brightest and flattest. Eye highlights and mouth detail remain readable. Workbench shadows remain simplified. Ground contact is visible in the full-body shots because the lighting comparisons crop the feet.
- Recommended defaults are the **medium_two** camera and **daylight** lighting.

## Corrections

| Original | Issue and cause | Review output |
| --- | --- | --- |
| studies/camera_presets/medium_single.png | Cosmetic. Aarav's hands crowd the bottom edge because the camera is close and aimed high. | The revised camera pulls back slightly and lowers its aim. Both hands now have visible clearance. |
| Missing Aanya medium still | Coverage gap. Aanya only had a solo close-up. | Added medium_aanya with matching framing and verified both hands and the hijab remain visible. |
| studies/camera_presets/over_shoulder.png | Earlier subject orientation obscures Aanya's face. | Retain the existing shoulder_revision still. |

The camera preset and its test were backed up before editing. Only the two affected medium stills were rendered under output/stage13_cinematic_previews/visual_review. The source previews are available for comparison.

## Verification

All 236 PNGs checked before creating the movement sheet passed integrity and decode checks. All nine silent MP4s decoded at 640 × 360, 12 fps and 24 frames each. No entirely dark frame appeared in the decoded frame check. All 216 camera poses matched the interpolation metadata. The 28 targeted tests passed with zero failures and skips. They cover camera presets and movement, Stage 4.3 facial geometry, Stage 4.4 timeline, Stage 5 story and audio, and Stage 6 assembly. All 168 protected SHA-256 hashes matched the Stage 13 baseline. Stage 12 animation logic was untouched.

## Stage 12 human review checklist

The Stage 12 report records 182 passing tests and a passing pre-push check. Human approval was confirmed by the user.

- [ ] Play both solo walks and the paired walk. Check foot contact, sliding and arm swing.
- [ ] Check wave and point readability, hand direction and settling.
- [ ] Review both nods and head shakes for smooth starts and stops.
- [ ] Check expression changes, gaze and blinking.
- [ ] Play both talking clips with audio and check mouth closure, rest and viseme timing.
- [ ] Check paired greeting, mutual gaze, reaction timing and dance.
- [ ] Check Aanya's hijab for alignment and collar intersections.
- [ ] Check attachment and deformation around shoulders, elbows, wrists and legs.

## Proposed 24-second sequence

After both approvals, use 640 × 360 at 12 fps. Allocate 3 seconds to the garden, 3 to Aarav's introduction, 3 to Aanya's response, 5 to conversation, 3 to a gesture, 3 to a reaction close-up and 4 to the closing two-shot. Reuse Stage 12 pose, blink, expression and gaze controls and existing Stage 5 WAV and viseme files. Keep the speaker and listener on consistent sides of the conversation axis. Place dialogue by frame and mirror the timing in a single PCM audio timeline. Use direct cuts for dialogue and short fades at the outer boundaries. Assemble 288 frames and a single audio encode with FFmpeg, then check decoding, frame count, cuts, black frames and audio timing.

The user approved both prerequisites. The 24-second sequence was subsequently rendered and awaits its own human visual and audio review. See stage13_cinematic_camera_report.md for validation.
