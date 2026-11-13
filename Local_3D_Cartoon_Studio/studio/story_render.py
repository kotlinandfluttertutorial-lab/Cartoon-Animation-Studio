"""Resumable Workbench rendering and FFmpeg assembly for prepared stories."""

import hashlib
import json
from pathlib import Path
from shutil import copyfile
import struct
import subprocess
import time
import zlib

from studio.story_planner import load_story

PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "blender" / "scripts"
GARDEN = PROJECT / "blender/assets/environments/garden/garden.blend"
RENDERER = SCRIPTS / "render_story_scene.py"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def valid_frame(path, width, height):
    """Check resolution and chunk checksums before reusing a frame."""
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return False
    if not data.startswith(PNG_SIGNATURE) or len(data) < 45:
        return False
    if data[12:16] != b"IHDR" or struct.unpack_from(">II", data, 16) != (width, height):
        return False
    offset = 8
    has_image_data = False
    while offset + 12 <= len(data):
        size, kind = struct.unpack_from(">I4s", data, offset)
        end = offset + 8 + size
        if end + 4 > len(data):
            return False
        crc = struct.unpack_from(">I", data, end)[0]
        if zlib.crc32(data[offset + 4:end]) != crc:
            return False
        has_image_data |= kind == b"IDAT"
        offset = end + 4
        if kind == b"IEND":
            return has_image_data and size == 0 and offset == len(data)
    return False


def input_file(directory, relative):
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        raise ValueError(f"Missing or invalid prepared input: {relative}")
    return path


def read_inputs(source):
    story_path = input_file(source, "story.json")
    timing_path = input_file(source, "timing.json")
    story = load_story(story_path)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    fps = timing["fps"]
    if type(fps) is not int or not 1 <= fps <= 60 or len(timing["scenes"]) != len(story.scenes):
        raise ValueError("The timing file does not match the prepared story.")
    dependencies = [
        story_path, timing_path, GARDEN, Path(__file__),
        *sorted(SCRIPTS.glob("*.py")), *sorted((PROJECT / "studio/dialogue").glob("*.py")),
    ]
    for character in story.characters:
        name = character.lower()
        dependencies.append(PROJECT / f"blender/assets/characters/{name}/{name}_stage4.blend")
    scenes = []
    next_start = 1
    for plan, timing_scene in zip(story.scenes, timing["scenes"], strict=True):
        duration = plan.duration_seconds * fps
        if timing_scene["start_frame"] != next_start or timing_scene["duration_frames"] != duration:
            raise ValueError("Scene starts and durations must match the story.")
        next_start += duration
        audio = input_file(source, timing_scene["mix"])
        dependencies.append(audio)
        lines = []
        expected = []
        if plan.narration:
            expected.append(("Narrator", plan.narration, "neutral"))
        expected.extend((line.character, line.text, line.emotion) for line in plan.dialogue)
        if len(timing_scene["lines"]) != len(expected):
            raise ValueError("Dialogue timing does not match the story lines.")
        next_line = 1
        for line, identity in zip(timing_scene["lines"], expected, strict=True):
            start, count = line["start_frame"], line["duration_frames"]
            if (
                (line["character"], line["text"], line["emotion"]) != identity
                or type(start) is not int or type(count) is not int
                or start < next_line or count <= 0 or start + count - 1 > duration
                or not 0 < line["duration_seconds"] <= count / fps
            ):
                raise ValueError("A dialogue line or its timing is invalid.")
            next_line = start + count
            item = {**line, "shapes": {}}
            if line["character"] != "Narrator":
                lipsync = input_file(source, line["lipsync"])
                dependencies.append(lipsync)
                shapes = json.loads(lipsync.read_text(encoding="utf-8"))
                if (shapes["fps"], shapes["total_frames"], shapes["character"]) != (
                    fps, count, line["character"],
                ):
                    raise ValueError("A lip-sync clip does not match its dialogue timing.")
                item["shapes"] = shapes["frames"]
            lines.append(item)
        scenes.append((plan, audio, lines))
    return story, fps, scenes, dependencies


def fingerprint(paths, profile):
    digest = hashlib.sha256(repr(profile).encode())
    for path in paths:
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def invoke(command, timeout=120):
    try:
        result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{Path(command[0]).name} timed out.") from exc
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} failed. {(result.stderr or result.stdout)[-2400:]}")
    return result.stdout


def srt_timestamp(seconds):
    millis = round(seconds * 1000)
    minutes, ms = divmod(millis, 60_000)
    hours, minute = divmod(minutes, 60)
    second, ms = divmod(ms, 1000)
    return f"{hours:02}:{minute:02}:{second:02},{ms:03}"


def subtitles(scenes, fps):
    blocks = []
    offset = 0
    for plan, _, lines in scenes:
        for line in lines:
            start = offset + (line["start_frame"] - 1) / fps
            end = start + line["duration_seconds"]
            text = " ".join(line["text"].split())
            blocks.append(
                f"{len(blocks) + 1}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n"
                f"{line['character']}: {text}\n"
            )
        offset += plan.duration_seconds
    return "\n".join(blocks)


def assemble(output, scenes, timing_fps, profile, settings):
    width, height, fps = profile
    ffmpeg = [settings.ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-nostdin"]
    subtitles_path = output / "subtitles.srt"
    captions = subtitles(scenes, timing_fps)
    subtitles_path.write_text(captions, encoding="utf-8")
    audio_directory = output / "audio"
    audio_directory.mkdir(exist_ok=True)
    tracks = []
    audio_tracks = []
    for index, (plan, audio, _) in enumerate(scenes, 1):
        directory = output / "scenes" / f"scene_{index:02}"
        segment = directory / "segment.mp4"
        scene_audio = audio_directory / f"scene_{index:02}.wav"
        copyfile(audio, scene_audio)
        # Scene segments are derived files and can be rebuilt from verified frames.
        invoke(ffmpeg + [
            "-y", "-framerate", str(fps), "-start_number", "1", "-i", str(directory / "frame_%04d.png"),
            "-i", str(scene_audio), "-map", "0:v", "-map", "1:a",
            "-t", str(plan.duration_seconds), "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "1",
            "-af", f"apad=whole_dur={plan.duration_seconds},afade=t=in:d=0.1,afade=t=out:st={plan.duration_seconds - 0.15}:d=0.15",
            str(segment),
        ])
        tracks.extend((f"file 'scenes/scene_{index:02}/segment.mp4'", f"duration {plan.duration_seconds}"))
        # Concatenate PCM before encoding AAC so encoder padding occurs only once.
        normalized = audio_directory / f"scene_{index:02}_master.wav"
        invoke(ffmpeg + [
            "-y", "-i", str(scene_audio), "-t", str(plan.duration_seconds),
            "-ar", "44100", "-ac", "1",
            "-af", f"apad=whole_dur={plan.duration_seconds},afade=t=in:d=0.1,afade=t=out:st={plan.duration_seconds - 0.15}:d=0.15",
            str(normalized),
        ])
        audio_tracks.append(f"file 'audio/{normalized.name}'")
    playlist = output / "segments.txt"
    playlist.write_text("\n".join(tracks) + "\n", encoding="ascii")
    audio_playlist = output / "audio_segments.txt"
    audio_playlist.write_text("\n".join(audio_tracks) + "\n", encoding="ascii")
    muxed = output / "assembly.partial.mp4"
    args = ffmpeg + [
        "-y", "-f", "concat", "-safe", "1", "-i", str(playlist),
        "-f", "concat", "-safe", "1", "-i", str(audio_playlist),
    ]
    if captions:
        args += ["-i", str(subtitles_path), "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:s", "mov_text"]
    else:
        args += ["-map", "0:v", "-map", "1:a"]
    invoke(args + ["-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", str(muxed)])
    metadata = json.loads(invoke([
        settings.ffprobe_executable, "-v", "error", "-count_frames", "-show_streams",
        "-show_format", "-of", "json", str(muxed),
    ]))
    video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    duration = sum(plan.duration_seconds for plan, _, _ in scenes)
    if (
        (video["width"], video["height"], video["r_frame_rate"]) != (width, height, f"{fps}/1")
        or int(video["nb_read_frames"]) != duration * fps
        or abs(float(metadata["format"]["duration"]) - duration) > 0.12
        or not any(stream["codec_type"] == "audio" for stream in metadata["streams"])
        or (captions and not any(stream["codec_type"] == "subtitle" for stream in metadata["streams"]))
    ):
        raise RuntimeError("FFprobe reported an unexpected frame count, stream, or duration.")
    invoke(ffmpeg + ["-xerror", "-i", str(muxed), "-map", "0:v", "-map", "0:a", "-f", "null", "-"])
    # Rename fails if a completed video already exists on the target Windows host.
    muxed.rename(output / "final_video.mp4")
    return metadata


def render_story(source, output, profile, settings, resume=False, budget=None, *, visual_upgrade=False):
    source, output = source.resolve(), output.resolve()
    width, height, fps = profile
    story, timing_fps, scenes, files = read_inputs(source)
    identity = fingerprint(files, (profile, "garden-upgrade") if visual_upgrade else profile)
    progress = output / "progress.json"
    if (output / "final_video.mp4").exists():
        raise ValueError("The final video already exists. Choose a new output directory.")
    if output.exists():
        if not resume or not progress.is_file():
            raise ValueError("Choose a new directory or resume a previously initialized render.")
        state = json.loads(progress.read_text(encoding="utf-8"))
        if state["fingerprint"] != identity:
            raise ValueError("Render inputs or quality settings changed. Use a new output directory.")
    else:
        output.mkdir(parents=True)
        state = {"fingerprint": identity, "scenes": {}}
        atomic_json(progress, state)

    started = time.perf_counter()
    reused = 0
    rendered = 0
    for index, (plan, _, lines) in enumerate(scenes, 1):
        directory = output / "scenes" / f"scene_{index:02}"
        directory.mkdir(parents=True, exist_ok=True)
        total = plan.duration_seconds * fps
        missing = [
            frame for frame in range(1, total + 1)
            if not valid_frame(directory / f"frame_{frame:04}.png", width, height)
        ]
        reused += total - len(missing)
        requested = missing if budget is None else missing[:max(0, budget - rendered)]
        if requested:
            job = directory / "job.json"
            atomic_json(job, {
                "scene": plan.model_dump(), "output": str(directory), "width": width, "height": height,
                "fps": fps, "timing_fps": timing_fps, "total_frames": total,
                "lines": lines, "frames": requested,
                "visual_upgrade": visual_upgrade,
            })
            with (directory / "blender.log").open("a", encoding="utf-8") as log:
                result = subprocess.run([
                    settings.blender_executable, "-b", str(GARDEN), "--python-exit-code", "1",
                    "--python", str(RENDERER), "--", str(job),
                ], stdout=log, stderr=subprocess.STDOUT, timeout=settings.process_timeout_seconds)
            if result.returncode or any(
                not valid_frame(directory / f"frame_{frame:04}.png", width, height)
                for frame in requested
            ):
                raise RuntimeError(f"Blender did not finish the requested frames. See {directory / 'blender.log'}.")
            rendered += len(requested)
        remaining = len(missing) - len(requested)
        state["scenes"][str(index)] = {"valid_frames": total - remaining, "total_frames": total}
        atomic_json(progress, state)
        if remaining:
            return {"status": "paused", "rendered": rendered, "reused": reused}

    metadata = assemble(output, scenes, timing_fps, profile, settings)
    report = {
        "status": "complete", "story": story.title, "width": width, "height": height, "fps": fps,
        "duration_seconds": story.duration_seconds, "rendered": rendered, "reused": reused,
        "elapsed_seconds": round(time.perf_counter() - started, 2), "probe": metadata,
    }
    atomic_json(output / "production_report.json", report)
    return {key: value for key, value in report.items() if key != "probe"}
