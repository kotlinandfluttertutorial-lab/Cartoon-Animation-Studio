# Stage 5 story and dialogue validation

## Implemented

`stage5_story.py` plans a cartoon from a story idea and target duration with local Ollama Qwen3 4B. The same strict schema accepts manual JSON through `--story`. It validates cast, supported actions and expressions, camera presets, scene totals, and sound cue positions before processing.

With `--piper-studio`, the command uses the existing Piper installation in its own Windows Python environment. It writes one WAV per spoken line, keeps narration separate, and derives exact durations from PCM sample counts. Character voice names and speeds are independently configurable. The audio stage writes a frame schedule, activity-gated viseme JSON, original synth music and cue WAVs, and an FFmpeg scene mix. The Blender dialogue renderer can use the expression specified in the viseme JSON.

The Piper adapter redirects its log to the new project output directory. The sibling studio remains a read-only dependency. No packages or voice models were installed.

## Reproduction

Run the following from the studio directory with the local Ollama service running and the Windows Piper studio available. Use a new output directory.

```powershell
python stage5_story.py --idea "Aarav and Aanya spot a bird in the garden" --duration 10 --output output/stage5_bird --piper-studio <path-to-existing-piper-studio>
```

For manual planning, replace `--idea` and `--duration` with `--story <path-to-story.json>`. Omit `--piper-studio` to write the validated story only. `--aarav-voice`, `--aanya-voice`, `--aarav-speed`, and `--aanya-speed` configure the two voice performances.

## Sample results and scope

Ollama generated a valid 10-second single-scene plan. The demonstration lengthened both lines through the manual JSON path to give the mouth movements enough screen time. In the final take, Piper synthesized separate tracks of 1.881 seconds for Aarav and 1.544 seconds for Aanya. The FFmpeg mix contains both voices, a quiet synth bed, and the bird cue at second 5.

The dialogue proof decoded successfully with 47 frames at 640 x 360 and 12 fps plus AAC audio. The assistant inspected REST, OPEN, and EI frames for both characters. The full pre-push run passed 170 tests and exited 0, with two warnings for local changes and tracked backup files. All 10 targeted tests passed after adding a terminal rest frame for speech that extends into the final audio frame.

Only Ryan was installed locally. The demo uses that voice for both characters with different speaking speeds. The mouth shapes follow WAV activity and approximate text timing. The dialogue preview consists of solo character cuts with the corresponding audio. Full garden blocking, camera and action execution from the story plan, and the production render pipeline are Stage 6 work.
