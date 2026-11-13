"""Local Streamlit interface for story planning, audio, previews, and renders."""

from pathlib import Path
import os
import shutil

import streamlit as st

from studio.story_planner import Story, load_story
from studio.story_render import PROJECT, atomic_json, input_file
from studio.ui_jobs import import_prepared, jobs, new_directory, project_path, read_json, start_job

ASSETS = PROJECT / "blender" / "assets"
WORKSPACE = Path(os.environ.get("CARTOON_STUDIO_PROJECTS", PROJECT / "output" / "studio_ui")).resolve()
ACTIONS = ("idle", "walk", "wave", "point", "nod", "greeting", "dance", "turn")
EXPRESSIONS = ("neutral", "happy", "surprised", "sad", "thinking", "excited")
CAMERAS = ("wide", "medium", "close", "approach", "follow", "pullback")
PROFILES = {"preview": "Preview · 640 × 360 · 12 fps", "720p": "Production · 1280 × 720 · 24 fps"}
DEFAULT_VOICE = "en_US-ryan-medium"
TITLE = "Cartoon Animation Studio"

st.set_page_config(page_title=TITLE, page_icon=":material/movie:", layout="wide")
st.session_state.setdefault("active_project", "magical-garden")


def selected_project():
    return project_path(WORKSPACE, st.session_state.active_project)


def latest_plan(project):
    return next(iter(sorted((project / "plans").glob("*/story.json"), reverse=True)), None)


def story_path(project):
    draft = project / "story.json"
    return draft if draft.is_file() else latest_plan(project)


def save_story(project, story):
    project.mkdir(parents=True, exist_ok=True)
    atomic_json(project / "story.json", story.model_dump())


def prepared_packages(project):
    return [
        path.parent for path in sorted((project / "prepared").glob("*/timing.json"), reverse=True)
    ]


def renders(project):
    for path in sorted((project / "renders").glob("*/production_report.json"), reverse=True):
        data = read_json(path)
        video = path.parent / "final_video.mp4"
        if data.get("status") == "complete" and video.is_file() and video.stat().st_size:
            yield path.parent, data


def launch(project, kind, args, output):
    try:
        start_job(project, kind, args, output)
    except (OSError, ValueError) as exc:
        st.error(str(exc))
    else:
        st.success("Job started. You can continue working while it runs.")


@st.fragment(run_every="2s")
def activity(project):
    latest = next(jobs(project), None)
    if latest is None:
        st.caption("No jobs started for this project.")
        return
    directory, job, result = latest
    status = result["status"]
    labels = {"plan": "Story generation", "audio": "Voice and audio preparation", "render": "Blender render"}
    label = f"{labels[job['kind']]} · {status.capitalize()}"
    if status == "complete":
        st.success(label)
    elif status in ("failed", "interrupted"):
        st.error(result.get("message", label), title=label)
    elif status == "paused":
        st.warning("Frames are saved. Resume from Render settings.", title=label)
    else:
        st.info("Processing in the background.", title=label)
    if job["kind"] == "render":
        target = Path(job["output"])
        frame_count = sum(1 for _ in (target / "scenes").glob("*/frame_[0-9][0-9][0-9][0-9].png"))
        timing = read_json(Path(job["args"][0]) / "timing.json")
        fps = timing.get("fps", 0)
        if fps:
            render_fps = 24 if "720p" in job["args"] else fps
            total = sum(scene["duration_frames"] for scene in timing["scenes"]) * render_fps // fps
            if total:
                st.progress(min(frame_count / total, 1.0), text=f"{frame_count} of {total} frames written")
    log = directory / "process.log"
    if log.is_file():
        details = st.expander("Job log", on_change="rerun")
        if details.open:
            with details, log.open("rb") as file:
                file.seek(max(0, log.stat().st_size - 6000))
                st.code(file.read().decode("utf-8", errors="replace"), language="text")


def dashboard():
    project = selected_project()
    st.title(TITLE)
    st.caption("Plan a story, prepare voices, and render an animated short on this computer.")
    primary, summary = st.columns([1.8, 1], gap="large")
    with primary:
        st.image(
            ASSETS / "environments/garden/previews/garden_with_characters.png",
            alt="Aarav and Aanya in the cartoon garden", width="stretch",
        )
    with summary:
        with st.container(border=True):
            st.subheader("Project overview")
            plan = story_path(project)
            story = load_story(plan) if plan else None
            st.write(story.title if story else "Start with a story idea.")
            columns = st.columns(2)
            columns[0].metric("Scenes", len(story.scenes) if story else 0)
            columns[1].metric("Duration", f"{story.duration_seconds} s" if story else "—")
            st.page_link(story_page, label="Open story generator", icon=":material/edit_note:", width="stretch")
        with st.container(border=True):
            st.subheader("Render activity")
            activity(project)


def story_generator():
    project = selected_project()
    st.title("Story generator")
    with st.form("generate_story"):
        idea = st.text_area("Story idea", placeholder="Aarav and Aanya spot a bird in the garden…")
        duration = st.number_input("Target duration in seconds", min_value=2, max_value=120, value=10)
        if st.form_submit_button("Generate with Ollama", type="primary"):
            if not idea.strip():
                st.error("Enter a story idea.")
            else:
                output = new_directory(project / "plans")
                launch(project, "plan", ["--idea", idea.strip(), "--duration", duration, "--output", output], output)

    generated = latest_plan(project)
    if generated and st.button("Use latest generated story"):
        save_story(project, load_story(generated))
        st.success("Generated story saved to this project.")

    path = story_path(project)
    initial = path.read_text(encoding="utf-8") if path else ""
    st.subheader("Manual story JSON")
    with st.form("manual_story"):
        content = st.text_area("Story JSON", value=initial, height=300, key=f"json_{project.name}_{hash(initial)}")
        if st.form_submit_button("Validate and save story"):
            try:
                save_story(project, Story.model_validate_json(content))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
            else:
                st.success("Story saved.")
    activity(project)


def characters():
    st.title("Character library")
    for column, name, description in zip(
        st.columns(2), ("Aarav", "Aanya"), ("Rigged character with a rounded crown.", "Rigged character with an articulated head and hijab."),
        strict=True,
    ):
        with column, st.container(border=True):
            st.subheader(name)
            st.image(
                ASSETS / f"characters/{name.lower()}/previews/three_quarter.png",
                alt=f"{name} in three-quarter view", width="stretch",
            )
            st.caption(description)
    st.page_link(scenes_page, label="Edit the cast in Scene editor", icon=":material/movie:")


def environments():
    st.title("Environment library")
    st.subheader("Garden")
    view = st.segmented_control("Camera view", ("Wide", "Medium", "Close"), default="Medium") or "Medium"
    file = {"Wide": "garden_wide.png", "Medium": "garden_main.png", "Close": "garden_close.png"}[view]
    st.image(ASSETS / "environments/garden/previews" / file, alt=f"{view} view of the garden", width="stretch")
    st.caption("The garden is the available production environment.")


def edit_scene(animation_only=False):
    project = selected_project()
    st.title("Animation controls" if animation_only else "Scene editor")
    path = story_path(project)
    if path is None:
        st.info("Create or load a story to edit its scenes.")
        return
    story = load_story(path)
    data = story.model_dump()
    index = st.selectbox("Scene", range(len(story.scenes)), format_func=lambda i: story.scenes[i].title)
    scene = data["scenes"][index]
    cast = [item["character"] for item in scene["performances"]]
    if not animation_only:
        chosen = st.multiselect("Cast", story.characters, default=cast, key=f"cast_{project.name}_{index}")
    else:
        chosen = cast
    by_name = {item["character"]: item for item in scene["performances"]}
    with st.form(f"scene_{project.name}_{index}_{animation_only}"):
        if not animation_only:
            scene["title"] = st.text_input("Scene title", scene["title"])
            scene["duration_seconds"] = st.number_input("Seconds", 2, 60, scene["duration_seconds"])
            scene["camera"] = st.selectbox("Camera", CAMERAS, CAMERAS.index(scene["camera"]))
        performances = []
        for name in chosen:
            item = by_name.get(name, {"action": "idle", "expression": "neutral"})
            action, expression = st.columns(2)
            action_name = action.selectbox(f"{name} action", ACTIONS, ACTIONS.index(item["action"]))
            performances.append({
                "character": name,
                "action": action_name,
                "expression": expression.selectbox(f"{name} expression", EXPRESSIONS, EXPRESSIONS.index(item["expression"])),
                "entrance": st.checkbox(f"{name} walks into the scene", value=item.get("entrance", False))
                and action_name == "walk",
            })
        if st.form_submit_button("Save scene", type="primary"):
            scene["performances"] = performances
            data["duration_seconds"] = sum(item["duration_seconds"] for item in data["scenes"])
            try:
                save_story(project, Story.model_validate(data))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
            else:
                st.success("Scene saved. Prepare audio again to render this revision.")
        if not animation_only:
            for line in scene["dialogue"]:
                st.caption(f"{line['character']} · {line['text']}")


def scene_editor():
    edit_scene()


def animation():
    edit_scene(animation_only=True)


def voices():
    project = selected_project()
    st.title("Dialogue and voice")
    path = story_path(project)
    if path:
        story = load_story(path)
        index = st.selectbox("Dialogue scene", range(len(story.scenes)), format_func=lambda i: story.scenes[i].title)
        data = story.model_dump()
        scene = data["scenes"][index]
        with st.form(f"dialogue_{project.name}_{index}"):
            scene["narration"] = st.text_area("Narration", value=scene["narration"], max_chars=300)
            for number, line in enumerate(scene["dialogue"], 1):
                label = f"{line['character']} line {number}"
                line["text"] = st.text_area(label, value=line["text"], max_chars=300)
                line["emotion"] = st.selectbox(f"{label} expression", EXPRESSIONS, EXPRESSIONS.index(line["emotion"]))
            if st.form_submit_button("Save dialogue"):
                try:
                    save_story(project, Story.model_validate(data))
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Dialogue saved. Prepare audio to render the new lines.")
    saved = read_json(project / "voice_settings.json")
    with st.form("piper_settings"):
        runtime = st.text_input("Existing Piper studio directory", value=saved.get("runtime", ""))
        settings = {"runtime": runtime}
        for column, name, speed in zip(st.columns(2), ("aarav", "aanya"), (0.95, 1.12), strict=True):
            settings[name] = column.text_input(f"{name.title()} voice model", value=saved.get(name, DEFAULT_VOICE))
            settings[f"{name}_speed"] = column.number_input(
                f"{name.title()} speed", 0.5, 2.0, float(saved.get(f"{name}_speed", speed)), 0.05,
            )
        if st.form_submit_button("Save settings and prepare audio", type="primary", disabled=path is None):
            if not runtime.strip():
                st.error("Enter the directory of the existing Piper studio.")
            else:
                output = new_directory(project / "prepared")
                snapshot = new_directory(project / "inputs").with_suffix(".json")
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, snapshot)
                atomic_json(project / "voice_settings.json", settings)
                args = ["--story", snapshot, "--output", output, "--piper-studio", runtime.strip()]
                for name in ("aarav", "aanya"):
                    args.extend((f"--{name}-voice", settings[name], f"--{name}-speed", settings[f"{name}_speed"]))
                launch(project, "audio", args, output)

    with st.expander("Import a prepared Stage 5 package"):
        with st.form("import_prepared"):
            source = st.text_input("Prepared package directory")
            if st.form_submit_button("Import package"):
                try:
                    if not source.strip():
                        raise ValueError("Enter the prepared package directory.")
                    target = new_directory(project / "prepared")
                    import_prepared(Path(source.strip()), target)
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Prepared story and audio imported.")
    activity(project)


def choose_package(project):
    packages = prepared_packages(project)
    if not packages:
        st.info("Prepare audio or import a Stage 5 package in Dialogue and voice.")
        return None
    return st.selectbox(
        "Prepared story", packages,
        format_func=lambda path: f"{load_story(path / 'story.json').title} · {path.name}",
    )


def preview():
    project = selected_project()
    st.title("Preview")
    complete = list(renders(project))
    if complete:
        selected, data = st.selectbox(
            "Completed render", complete,
            format_func=lambda pair: f"{pair[1]['story']} · {pair[1]['width']} × {pair[1]['height']}",
        )
        srt = selected / "subtitles.srt"
        subtitles = srt if srt.is_file() and srt.stat().st_size else None
        st.video(selected / "final_video.mp4", subtitles=subtitles, alt="Completed cartoon animation")
        st.caption(f"{data['duration_seconds']} seconds · {data['fps']} fps")
    else:
        st.info("Completed previews appear here after the render is verified.")
    package = choose_package(project)
    if package:
        timing = read_json(package / "timing.json")
        scene = st.selectbox("Scene audio", timing["scenes"], format_func=lambda row: row["title"])
        st.audio(input_file(package, scene["mix"]), format="audio/wav", alt="Prepared scene audio mix")


def render_settings():
    project = selected_project()
    st.title("Render settings")
    package = choose_package(project)
    if package:
        quality = st.segmented_control(
            "Output quality", list(PROFILES), format_func=PROFILES.__getitem__, default="preview", key="render_quality",
        ) or "preview"
        target = project / "renders" / f"{package.name}-{quality}"
        final = (target / "final_video.mp4").is_file()
        complete = final and read_json(target / "production_report.json").get("status") == "complete"
        resume = (target / "progress.json").is_file() and not final
        if complete:
            st.success("A completed file already exists for this package and profile.")
            st.page_link(preview_page, label="Open preview", icon=":material/play_circle:")
        elif final:
            st.warning("A video exists without a completed verification report. See the job log.")
        else:
            with st.form("render_form"):
                budget = st.number_input("Pause after new frames (0 renders to completion)", min_value=0, value=0)
                if st.form_submit_button("Resume render" if resume else "Start render", type="primary"):
                    args = [package, target, "--quality", quality]
                    if resume:
                        args.append("--resume")
                    if budget:
                        args.extend(("--frame-budget", budget))
                    launch(project, "render", args, target)
    activity(project)


def reports():
    project = selected_project()
    st.title("Production reports")
    complete = list(renders(project))
    if not complete:
        st.info("A production report is available once a render has passed validation.")
        return
    directory, report = st.selectbox(
        "Production", complete,
        format_func=lambda pair: f"{pair[1]['story']} · {pair[0].name}",
    )
    for column, (label, value) in zip(st.columns(3), (
        ("Duration", f"{report['duration_seconds']} s"), ("Resolution", f"{report['width']} × {report['height']}"),
        ("Frames reused", report["reused"]),
    ), strict=True):
        column.metric(label, value)
    st.download_button(
        "Download report", (directory / "production_report.json").read_bytes(), "production_report.json",
        mime="application/json", icon=":material/download:",
    )
    if os.name == "nt" and st.button("Open output folder", icon=":material/folder_open:"):
        try:
            os.startfile(directory)
        except OSError as exc:
            st.error(str(exc))
    st.code(str(directory), language="text")


dashboard_page = st.Page(dashboard, title="Dashboard", icon=":material/dashboard:", default=True)
story_page = st.Page(story_generator, title="Story generator", icon=":material/edit_note:")
scenes_page = st.Page(scene_editor, title="Scene editor", icon=":material/movie:")
preview_page = st.Page(preview, title="Preview", icon=":material/play_circle:")
navigation = st.navigation({
    "Studio": [dashboard_page, story_page, scenes_page, st.Page(animation, title="Animation controls", icon=":material/animation:"),
               st.Page(voices, title="Dialogue and voice", icon=":material/mic:")],
    "Libraries": [st.Page(characters, title="Characters", icon=":material/person:"),
                  st.Page(environments, title="Environments", icon=":material/park:")],
    "Production": [preview_page, st.Page(render_settings, title="Render settings", icon=":material/tune:"),
                   st.Page(reports, title="Production reports", icon=":material/description:")],
})
with st.sidebar:
    with st.form("project_picker", border=False):
        name = st.text_input("Local project", value=st.session_state.active_project, key="project_name")
        if st.form_submit_button("Open project", width="stretch"):
            try:
                project_path(WORKSPACE, name.strip())
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.active_project = name.strip()
navigation.run()
