# Stage 7 studio interface

The local Streamlit interface opens on a dashboard with a project selector and the garden preview. It exposes ten pages covering story generation, scene and animation editing, dialogue and voice settings, both asset libraries, playback, render settings, and production reports.

## Workflow

1. Open a local project. Generate a draft with Ollama or paste a strict story JSON document.
2. Adjust scene title, duration, camera, cast, actions, expressions, narration, and dialogue. Prepare a new audio package after editing a draft.
3. Configure the existing Piper runtime and the two voices, or import a previously prepared Stage 5 package.
4. Choose the preview or 720p profile and start a render. A frame budget can deliberately pause the job. Render settings resumes the same prepared package and profile.
5. Play the verified MP4 and selectable subtitles on Preview. Production reports provides the report and Windows output-folder access.

Jobs run as background subprocesses, with on-disk state, frame progress, and logs. The UI waits for the render command and its successful production report before listing a video as complete. Work stays on the local machine.

## Running locally

From the studio directory, run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run studio_ui.py
```

The server binds to localhost. The Stage 1 smoke-test entry point remains `app.py`.

## Verification

- The live Streamlit test opened all ten pages, saved a manual story, edited dialogue, imported the Stage 5 package, and launched a render. The first job paused after three frames. Resume reused those frames and rendered the remaining 117.
- Separate live jobs generated a valid 10-second story with Ollama and prepared real Piper audio through the dialogue page.
- The verified output was a 10-second 640 x 360 MP4 at 12 fps with H.264 video, AAC audio, and a subtitle stream. Preview and Production reports both recognized it after the job finished.
- The final full suite passed all 180 tests. `check_before_push.py` exited 0 with 14 checks passed, 0 failures, 0 skips, and warnings for uncommitted changes and tracked backups. All 164 source asset hashes matched.
- The live application and controls were exercised through Streamlit's localhost API. Browser screenshot verification was unavailable because the computer-use tool could not initialize.
