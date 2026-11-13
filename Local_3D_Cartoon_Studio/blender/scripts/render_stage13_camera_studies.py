"""Render standalone camera and lighting studies with approved assets."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stage11_garden import PROJECT, load_cast
from facial_preview import mouth_surface
from garden_utils import set_camera
from stage13_camera import CAMERAS, LIGHTS, MOVEMENTS, camera_pose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--camera", choices=CAMERAS, help="render one camera still")
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.fps < 1 or min(args.width, args.height) < 2 or args.width % 2 or args.height % 2:
        parser.error("Supply a positive frame rate and positive even dimensions.")
    output = args.output.resolve()
    output.mkdir(parents=True)
    for folder in ("camera_presets", "lighting_presets", "camera_movements", "metadata"):
        (output / folder).mkdir()
    start = perf_counter()
    bpy.ops.wm.open_mainfile(filepath=str(PROJECT / "output/stage11_garden_previews/final/garden_stage11.blend"))
    scene = bpy.context.scene
    assert scene.render.engine == "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.resolution_percentage = 100
    scene.render.fps = args.fps
    scene.render.image_settings.file_format = "PNG"
    cast = load_cast(scene)
    scene.frame_set(13)
    camera = bpy.data.objects["Cast Medium Camera"]
    scene.camera = camera
    shading = scene.display.shading
    orientations = {name: root.rotation_euler.z for name, root, _, _ in cast}
    visibility = {obj: obj.hide_render for _, root, _, _ in cast for obj in root.children_recursive}
    settings = json.loads((PROJECT / "config/settings.json").read_text(encoding="utf-8"))
    report = {"engine": scene.render.engine, "resolution": [args.width, args.height],
              "fps": args.fps, "initialization_seconds": perf_counter() - start,
              "camera_presets": {}, "lighting_presets": {}, "camera_movements": {}}

    def lighting(preset):
        studio, exposure, shadow, cavity, background = LIGHTS[preset]
        shading.studio_light = studio
        scene.view_settings.exposure = exposure
        shading.show_shadows = True
        shading.shadow_intensity = shadow
        shading.cavity_valley_factor = cavity
        scene.world.color = background
        return shading.studio_light

    def compose(preset, movement="static", progress=0):
        spec = CAMERAS[preset]
        for name, root, _, _ in cast:
            root.rotation_euler.z = orientations[name] + (-1.7 if name == "Aarav" else .85) * (preset == "over_shoulder")
            for obj in root.children_recursive:
                obj.hide_render = visibility[obj] or name not in spec.subjects
                obj.hide_set(obj.hide_render)
        position, target = camera_pose(preset, movement, progress)
        set_camera(camera, position, target)
        camera.data.lens = spec.lens
        bpy.context.view_layer.update()
        bounds = {}
        for name in spec.subjects:
            suffixes = ("Head", "Foot_L", "Foot_R", "Hand_L", "Hand_R") if preset in (
                "full_body", "walking_follow", "side_tracking") else ("Head",)
            if preset == "over_shoulder" and name == "Aarav":
                continue
            for suffix in suffixes:
                part = bpy.data.objects[f"{name}_{suffix}"]
                points = [world_to_camera_view(scene, camera, part.matrix_world @ Vector(p))
                          for p in part.bound_box]
                limits = [min(p.x for p in points), min(p.y for p in points),
                          max(p.x for p in points), max(p.y for p in points)]
                assert min(limits[:2]) > .01 and max(limits[2:]) < .99 and min(
                    p.z for p in points) > camera.data.clip_start, (preset, name, suffix, limits)
                bounds[part.name] = limits
        return {"position": position, "target": target, "lens_mm": spec.lens,
                "subjects": spec.subjects, "projected_bounds": bounds}

    def render(path):
        scene.render.filepath = str(path)
        started = perf_counter()
        bpy.ops.render.render(write_still=True)
        return perf_counter() - started

    with ExitStack() as stack:
        for name, root, _, _ in cast:
            orientation = root.rotation_euler.z
            root.rotation_euler.z = 0
            stack.enter_context(mouth_surface(name, "happy"))
            root.rotation_euler.z = orientation

        lighting("daylight")
        for name in ([args.camera] if args.camera else CAMERAS):
            data = compose(name)
            data["render_seconds"] = render(output / "camera_presets" / f"{name}.png")
            report["camera_presets"][name] = data
        if args.camera:
            (output / "metadata/studies.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            return
        compose("conversation")
        for name in LIGHTS:
            studio = lighting(name)
            report["lighting_presets"][name] = {
                "studio_light": studio,
                "render_seconds": render(output / "lighting_presets" / f"{name}.png"),
            }

        lighting("morning")
        for name in MOVEMENTS:
            preset = "establishing" if name in ("pan", "tilt") else "medium_two"
            if name in ("follow", "track", "reveal"):
                preset = "walking_follow"
            frames = output / "camera_movements" / name
            frames.mkdir()
            count = args.fps * 2
            poses, seconds = [], 0
            for index in range(count):
                poses.append(compose(preset, name, index / (count - 1)))
                seconds += render(frames / f"{index:04}.png")
            video = frames.with_suffix(".mp4")
            encode = perf_counter()
            subprocess.run([settings["ffmpeg_executable"], "-nostdin", "-v", "error", "-n",
                            "-framerate", str(args.fps), "-i", str(frames / "%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
            encode = perf_counter() - encode
            subprocess.run([settings["ffmpeg_executable"], "-nostdin", "-v", "error",
                            "-xerror", "-i", str(video), "-f", "null", "-"], check=True)
            probe = json.loads(subprocess.check_output([settings["ffprobe_executable"], "-v", "error",
                                "-show_streams", "-of", "json", str(video)]))["streams"][0]
            assert (probe["width"], probe["height"], int(probe["nb_frames"]), probe["r_frame_rate"]) == (
                args.width, args.height, count, f"{args.fps}/1")
            report["camera_movements"][name] = {"preset": preset, "frames": count, "poses": poses,
                                                "render_seconds": seconds, "encode_seconds": encode,
                                                "bytes": video.stat().st_size}
    report["total_seconds"] = perf_counter() - start
    (output / "metadata/studies.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
