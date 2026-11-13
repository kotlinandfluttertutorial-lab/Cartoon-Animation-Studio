"""Render the Stage 13 seven-shot garden preview with Stage 12 performances."""

import argparse
from dataclasses import dataclass
import json
from math import floor
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stage11_garden import PROJECT, load_cast
from garden_utils import set_camera
from render_stage12_animation import FPS, Performer, blink_schedule, envelope, smooth, speech_lines
from stage13_camera import CAMERAS, LIGHTS, camera_pose


@dataclass(frozen=True)
class Shot:
    name: str
    seconds: int
    camera: str
    movement: str = "static"
    light: str = "daylight"


SHOTS = (
    Shot("garden", 3, "establishing", "pan"),
    Shot("aarav_intro", 3, "medium_single"),
    Shot("aanya_response", 3, "medium_aanya"),
    Shot("conversation", 5, "conversation", light="conversation"),
    Shot("gesture", 3, "full_body"),
    Shot("reaction", 3, "close_up", light="close_up"),
    Shot("closing", 4, "walking_follow", "pull_back"),
)
# One-based viseme frames start on these zero-based shot frames.
DIALOGUE = {"Aarav": 6, "Aanya": 33}
FADE_FRAMES = 4


def assemble(output, settings, speech, conversation_start, count):
    args = [settings["ffmpeg_executable"], "-nostdin", "-v", "error", "-n",
            "-framerate", str(FPS), "-i", str(output / "frames/%04d.png")]
    filters = []
    for index, (name, cue) in enumerate(DIALOGUE.items(), 1):
        args += ["-i", str(speech[name][3])]
        # 48 kHz is divisible by 12 fps, so dialogue starts at an exact sample.
        delay = (conversation_start + cue) * (48000 // FPS)
        filters.append(f"[{index}:a]aresample=48000,adelay={delay}S:all=1[a{index}]")
    filters.append(f"[a1][a2]amix=inputs=2:normalize=0,apad,atrim=end_sample={count*48000//FPS}[audio]")
    # Lift from a shaded opening and fade into shade at the end, preserving a
    # visible image on both boundary frames.
    video_filter = (
        f"fade=in:start_frame=0:nb_frames={FADE_FRAMES}:color=0x26342e,"
        f"fade=out:start_frame={count-FADE_FRAMES-1}:nb_frames={FADE_FRAMES}:color=0x26342e"
    )
    temporary = output / "verification.mp4"
    started = perf_counter()
    subprocess.run(args + ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[audio]",
                           "-vf", video_filter, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(temporary)], check=True)
    seconds = perf_counter() - started
    streams = json.loads(subprocess.check_output([settings["ffprobe_executable"], "-v", "error",
                                "-show_streams", "-of", "json", str(temporary)]))["streams"]
    video, audio = streams
    assert (video["width"], video["height"], video["r_frame_rate"], int(video["nb_frames"])) == (640, 360, f"{FPS}/1", count)
    assert video["codec_name"] == "h264" and audio["codec_name"] == "aac"
    assert abs(float(audio["duration"]) - count / FPS) <= .025
    check = subprocess.run([settings["ffmpeg_executable"], "-nostdin", "-v", "info", "-xerror",
                            "-i", str(temporary), "-vf", "blackdetect=d=0:pix_th=0.08",
                            "-f", "null", "-"], capture_output=True, text=True, check=True)
    assert not re.search(r"black_start:\s*\d", check.stderr), "Black frames detected"
    final = output / "final_video.mp4"
    temporary.rename(final)
    return {"encode_seconds": seconds, "bytes": final.stat().st_size, "streams": streams}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check-only", action="store_true", help="evaluate every frame without rendering")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    start = perf_counter()
    speech = speech_lines(PROJECT / "output/stage12_animation_previews/speech_source")
    for name, cue in DIALOGUE.items():
        fps, length, _, wav = speech[name]
        assert fps == FPS and cue + length <= 5 * FPS and wav.is_file()
    settings = json.loads((PROJECT / "config/settings.json").read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(PROJECT / "output/stage11_garden_previews/final/garden_stage11.blend"))
    scene = bpy.context.scene
    assert scene.render.engine == "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"
    cast = [Performer(item) for item in load_cast(scene)]
    visibility = {obj: obj.hide_render for p in cast for obj in p.root.children_recursive}
    camera = bpy.data.objects["Cast Medium Camera"]
    scene.camera = camera
    report = {"resolution": [640, 360], "fps": FPS, "engine": scene.render.engine,
              "initialization_seconds": perf_counter() - start, "shots": []}
    if not args.check_only:
        (output / "frames").mkdir(parents=True)
    frame = 0
    for shot in SHOTS:
        spec = CAMERAS[shot.camera]
        shot_start = frame
        count = shot.seconds * FPS
        studio, exposure, shadow, cavity, sky = LIGHTS[shot.light]
        shading = scene.display.shading
        shading.studio_light = studio
        shading.show_shadows = True
        shading.shadow_intensity = shadow
        shading.cavity_valley_factor = cavity
        scene.world.color = sky
        scene.view_settings.exposure = exposure
        camera.data.lens = spec.lens
        active = [p for p in cast if p.name in spec.subjects]
        for p in cast:
            for obj in p.root.children_recursive:
                obj.hide_render = visibility[obj] or p not in active
        blinks = {p.name: blink_schedule(1308 + i, shot.seconds) for i, p in enumerate(cast)}
        started = perf_counter()
        for n in range(count):
            t = n / FPS
            # The two garden birds have existing animated paths. Keep the
            # opening and the conversation on the same continuous timeline.
            scene.frame_set(frame + 1)
            position, target = camera_pose(shot.camera, shot.movement, n / (count - 1))
            set_camera(camera, position, target)
            for p in active:
                side = -1 if p.name == "Aarav" else 1
                mode, expression = "idle", "happy"
                gaze = (.12 * side, .12)
                viseme = None
                if shot.name == "conversation":
                    cue = DIALOGUE[p.name]
                    _, length, keys, _ = speech[p.name]
                    speech_frame = n - cue + 1
                    viseme = keys.get(speech_frame, "REST") if 1 <= speech_frame <= length else None
                    gaze = (-side * .80, .22 if p.name == "Aarav" else .08)
                    expression = "excited" if viseme and p.name == "Aarav" else "curious"
                elif shot.name == "gesture":
                    mode, expression = "pointing", "curious"
                    gaze = (-.67 * envelope(t, .35, 2.03), .36)
                elif shot.name == "reaction":
                    expression, gaze = "surprised", (-.36, .56)
                elif shot.name == "closing":
                    mode, expression = "camera_wave", "big_smile"
                x = 0 if shot.name == "gesture" else side * .62
                p.body(t, mode, shot.seconds, x, gaze, phase=.35 if shot.name == "gesture" else .85)
                blink = max((smooth(1 - abs(t - mark)/.14) for mark in blinks[p.name]), default=0)
                p.face(expression, .20 + .80 * envelope(t, 0, shot.seconds), gaze, blink, viseme)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            for p in active:
                parts = ("Head", "Hand_L", "Hand_R", "Foot_L", "Foot_R") if shot.name in ("gesture", "closing") else ("Head",)
                for name in parts:
                    part = p.parts[name]
                    if name == "Head":
                        origin = camera.matrix_world.translation
                        center = part.matrix_world.translation
                        ray = center - origin
                        hit, _, _, _, visible, _ = scene.ray_cast(depsgraph, origin, ray.normalized(), distance=ray.length+.02)
                        assert hit and visible in p.root.children_recursive, (shot.name, n, p.name, visible)
                    for corner in part.bound_box:
                        x, y, z = world_to_camera_view(scene, camera, part.matrix_world @ Vector(corner))
                        assert .005 < x < .995 and .005 < y < .995 and z > camera.data.clip_start, (shot.name, n, part.name, x, y)
            if not args.check_only:
                scene.render.filepath = str(output / "frames" / f"{frame:04d}.png")
                bpy.ops.render.render(write_still=True)
            frame += 1
        report["shots"].append({"name": shot.name, "start_frame": shot_start, "frames": count,
                                "camera": shot.camera, "movement": shot.movement, "light": shot.light,
                                "seconds_elapsed": perf_counter() - started})
    conversation_start = next(s["start_frame"] for s in report["shots"] if s["name"] == "conversation")
    report["dialogue"] = {name: {"frame": conversation_start + offset,
                                "seconds": (conversation_start + offset)/FPS}
                          for name, offset in DIALOGUE.items()}
    report["frame_count"] = frame
    report["duration_seconds"] = frame / FPS
    report["scarf_transform_error"] = max(p.max_scarf_error for p in cast)
    if not args.check_only:
        report["media"] = assemble(output, settings, speech, conversation_start, frame)
        report["total_seconds"] = perf_counter() - start
        (output / "sequence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {frame} frames across {len(SHOTS)} shots")


if __name__ == "__main__":
    main()
