"""Build a disposable comparison scene or benchmark one engine in Blender."""
import json
import sys
import time
from pathlib import Path

import bpy

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
sys.path.insert(0, str(PROJECT / "blender/scripts"))

def build():
    from garden_art_direction import dress_garden, soften_character
    from garden_utils import configure_workbench
    from facial_preview import prepare_character_face, mouth_surface
    from render_stage44_preview import append_character, flying_bird, camera_move
    from contextlib import ExitStack

    scene = bpy.context.scene
    configure_workbench(scene)
    dress_garden(scene)
    with ExitStack() as temporary:
        for character, x, angle in (("Aarav", -.75, 0), ("Aanya", .75, 3.14159265)):
            root = append_character(scene, character)
            prepare_character_face(character)
            soften_character(root)
            temporary.enter_context(mouth_surface(character, "happy"))
            root.location = (x, -.2, .012)
            root.rotation_euler.z = angle
        flying_bird(scene, "Audit bird", "#4BADE8", 1, 24, -.5, 2.2)
        pose = ((.25, 3.8, 2.18), (0, 0, 1.38), 5.55)
        scene.timeline_markers.clear()
        scene.camera = camera_move(scene, "Audit camera", 1, 24, pose, pose)
        scene.frame_set(9)
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        # Shared node setup for the two lighting engines. Workbench uses diffuse colors.
        for mat in bpy.data.materials:
            if mat.users:
                mat.use_nodes = True
                shader = mat.node_tree.nodes.get("Principled BSDF")
                if shader:
                    shader.inputs["Base Color"].default_value = mat.diffuse_color
                    shader.inputs["Roughness"].default_value = .72
        scene.world.use_nodes = True
        bg = scene.world.node_tree.nodes.get("Background")
        bg.inputs[0].default_value = (.32, .58, .77, 1)
        bg.inputs[1].default_value = .55
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "comparison.blend"))

def benchmark(engine, width, fps, count, tag):
    import gpu

    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = width
    scene.render.resolution_y = width * 9 // 16
    scene.render.fps = fps
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = 12
        scene.cycles.use_denoising = True
    elif engine == "BLENDER_EEVEE_NEXT":
        scene.eevee.taa_render_samples = 16
    result = dict(engine=engine, width=width, height=scene.render.resolution_y, fps=fps,
                  background=bpy.app.background, seconds=[], bytes=[])
    for i in range(count):
        scene.frame_set(9 + i * 24 // fps)
        path = OUT / f"{tag}_{i+1:02}.png"
        scene.render.filepath = str(path)
        t = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        result["seconds"].append(round(time.perf_counter()-t, 4))
        result["bytes"].append(path.stat().st_size)
    if not bpy.app.background:
        result["renderer"] = gpu.platform.renderer_get()
        result["driver"] = gpu.platform.version_get()
    (OUT / f"{tag}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

args = sys.argv[sys.argv.index("--")+1:]
if args == ["build"]:
    build()
else:
    engine, width, fps, count, tag = args
    def run():
        try:
            benchmark(engine, int(width), int(fps), int(count), tag)
        except Exception:
            import traceback
            (OUT / f"{tag}.error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            if bpy.app.background:
                raise
        if not bpy.app.background:
            bpy.ops.wm.quit_blender()
    if bpy.app.background:
        run()
    else:
        bpy.app.timers.register(run, first_interval=2)
