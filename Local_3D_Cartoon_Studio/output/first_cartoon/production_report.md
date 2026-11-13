# Two Friends in the Magical Garden

The final export contains six scenes and 1,080 frames at 1280 × 720 and 24 fps. The MP4 contains H.264 video, AAC audio, and eight selectable subtitle cues. A separate SRT accompanies it.

- All six PNG sequences passed frame count, resolution, and chunk integrity checks. The MP4 decoded successfully and FFmpeg detected zero black frames.
- A sampled voice segment from each scene matched its position in the decoded audio with no measured offset. Lip-sync uses approximate mouth shapes based on WAV activity and text.
- The resume check preserved all five existing frame hashes and rendered the remaining 1,075 frames. The resumed render and initial assembly took 495.97 seconds. The final audio reassembly reused the rendered frames.
- All 164 source asset hashes matched. Peak memory could not be measured.

The assistant inspected sample frames from every scene. The user approved the Stage 8 export for visual and audio sign-off. Both characters use the installed Ryan voice with different speaking speeds.
