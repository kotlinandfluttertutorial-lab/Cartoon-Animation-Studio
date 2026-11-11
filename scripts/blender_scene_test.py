"""
Stage 0 — Blender scene creation and render test script.
Runs inside Blender's embedded Python (blender --background --python <this>).

Creates: ground plane, cube, sphere, camera, sun light.
Renders: 5-second animation at 640x360, 12 FPS using the engine passed via
         environment variable BLENDER_ENGINE (WORKBENCH | EEVEE | CYCLES).

Writes timing data to: output/render_timing.json
"""

import bpy
import os
import sys
import json
import time
import math

# ── Configuration ────────────────────────────────────────────────────────────
ENGINE   = os.environ.get("BLENDER_ENGINE", "WORKBENCH")  # WORKBENCH / EEVEE / CYCLES
OUTDIR   = os.environ.get("BLENDER_OUTDIR",
           os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "frames"))
JSONOUT  = os.environ.get("BLENDER_JSONOUT",
           os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "render_timing.json"))
FPS      = 12
DURATION = 5          # seconds
TOTAL_FRAMES = FPS * DURATION   # 60
RESW, RESH   = 640, 360

os.makedirs(OUTDIR, exist_ok=True)

# ── Reset scene ───────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.name = "Stage0_Test"

# ── Render settings ──────────────────────────────────────────────────────────
scene.render.resolution_x        = RESW
scene.render.resolution_y        = RESH
scene.render.resolution_percentage = 100
scene.render.fps                 = FPS
scene.frame_start                = 1
scene.frame_end                  = TOTAL_FRAMES
scene.render.image_settings.file_format = "PNG"
# filepath not used since we save each frame explicitly

engine_map = {
    "WORKBENCH": "BLENDER_WORKBENCH",
    "EEVEE":     "BLENDER_EEVEE_NEXT",
    "CYCLES":    "CYCLES",
}
scene.render.engine = engine_map.get(ENGINE, "BLENDER_WORKBENCH")

if ENGINE == "CYCLES":
    scene.cycles.device          = "CPU"
    scene.cycles.samples         = 32          # low sample count for speed test
    scene.cycles.use_denoising   = False

if ENGINE == "EEVEE":
    scene.eevee.taa_render_samples = 16

# ── World / sky ───────────────────────────────────────────────────────────────
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.6, 0.8, 1.0, 1.0)   # light-blue sky
bg.inputs[1].default_value = 0.5

# ── Ground plane ─────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "Ground"
mat_ground = bpy.data.materials.new("Mat_Ground")
mat_ground.use_nodes = True
mat_ground.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.6, 0.2, 1)
plane.data.materials.append(mat_ground)

# ── Cube (animated position) ─────────────────────────────────────────────────
bpy.ops.mesh.primitive_cube_add(size=1.5, location=(-2, 0, 0.75))
cube = bpy.context.active_object
cube.name = "AnimCube"
mat_cube = bpy.data.materials.new("Mat_Cube")
mat_cube.use_nodes = True
mat_cube.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1)
cube.data.materials.append(mat_cube)

# Animate cube: bounce rotation over 60 frames
cube.rotation_euler = (0, 0, 0)
cube.keyframe_insert("rotation_euler", frame=1)
cube.rotation_euler = (0, 0, math.radians(360))
cube.keyframe_insert("rotation_euler", frame=TOTAL_FRAMES)

# ── Sphere ───────────────────────────────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(2, 0, 0.8), segments=24, ring_count=16)
sphere = bpy.context.active_object
sphere.name = "Sphere"
mat_sphere = bpy.data.materials.new("Mat_Sphere")
mat_sphere.use_nodes = True
mat_sphere.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.4, 0.9, 1)
mat_sphere.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.1
mat_sphere.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.3
sphere.data.materials.append(mat_sphere)

# Animate sphere: vertical bounce
sphere.location = (2, 0, 0.8)
sphere.keyframe_insert("location", frame=1)
sphere.location = (2, 0, 3.0)
sphere.keyframe_insert("location", frame=TOTAL_FRAMES // 2)
sphere.location = (2, 0, 0.8)
sphere.keyframe_insert("location", frame=TOTAL_FRAMES)

# ── Camera ───────────────────────────────────────────────────────────────────
cam_data = bpy.data.cameras.new("Camera")
cam_obj  = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (0, -8, 4)
cam_obj.rotation_euler = (math.radians(60), 0, 0)
scene.camera = cam_obj

# ── Sun light ────────────────────────────────────────────────────────────────
light_data = bpy.data.lights.new("Sun", type="SUN")
light_data.energy = 3.0
light_obj = bpy.data.objects.new("Sun", light_data)
scene.collection.objects.link(light_obj)
light_obj.location = (4, -4, 8)
light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))

# ── Render ────────────────────────────────────────────────────────────────────
print(f"[Stage0] Engine: {ENGINE}  Resolution: {RESW}x{RESH}  FPS: {FPS}  Frames: {TOTAL_FRAMES}")
print(f"[Stage0] Output: {OUTDIR}")

frame_times = []
render_start = time.perf_counter()

for frame in range(1, TOTAL_FRAMES + 1):
    scene.frame_set(frame)
    t0 = time.perf_counter()
    bpy.ops.render.render(write_still=False)
    # Save via the render result image directly
    frame_path = os.path.join(OUTDIR, f"frame_{frame:04d}.png")
    bpy.data.images["Render Result"].save_render(frame_path)
    elapsed = time.perf_counter() - t0
    frame_times.append(round(elapsed, 3))
    print(f"[Stage0] Frame {frame:03d}/{TOTAL_FRAMES}  {elapsed:.2f}s  -> {frame_path}")

total_render_time = time.perf_counter() - render_start
avg_frame_time    = sum(frame_times) / len(frame_times)

# ── Count output files ────────────────────────────────────────────────────────
png_files    = [f for f in os.listdir(OUTDIR) if f.lower().endswith(".png")]
total_bytes  = sum(os.path.getsize(os.path.join(OUTDIR, f)) for f in png_files)
frames_ok    = len(png_files)

# ── Write timing JSON ─────────────────────────────────────────────────────────
timing = {
    "engine":           ENGINE,
    "blender_engine_id": engine_map.get(ENGINE),
    "resolution":       f"{RESW}x{RESH}",
    "fps":              FPS,
    "total_frames":     TOTAL_FRAMES,
    "total_render_time_s": round(total_render_time, 2),
    "avg_frame_time_s": round(avg_frame_time, 3),
    "min_frame_time_s": round(min(frame_times), 3),
    "max_frame_time_s": round(max(frame_times), 3),
    "frames_rendered":  frames_ok,
    "output_dir":       OUTDIR,
    "total_output_bytes": total_bytes,
    "total_output_mb":  round(total_bytes / (1024*1024), 2),
    "frame_times":      frame_times,
}

os.makedirs(os.path.dirname(JSONOUT), exist_ok=True)
with open(JSONOUT, "w") as f:
    json.dump(timing, f, indent=2)

print(f"\n[Stage0] ✓ Render complete")
print(f"[Stage0] Total time : {total_render_time:.1f}s")
print(f"[Stage0] Avg frame  : {avg_frame_time:.2f}s")
print(f"[Stage0] Frames OK  : {frames_ok}/{TOTAL_FRAMES}")
print(f"[Stage0] Output size: {total_bytes/1024/1024:.1f} MB")
print(f"[Stage0] Timing JSON: {JSONOUT}")
