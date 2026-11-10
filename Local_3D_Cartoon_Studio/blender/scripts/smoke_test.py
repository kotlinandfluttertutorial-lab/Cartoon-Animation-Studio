"""Blender smoke test script — runs inside Blender's embedded Python."""
import bpy
import os
import json
import time
import math
from pathlib import Path

# Read config
config_path = os.environ.get("BLENDER_CONFIG_PATH", "")
if not config_path or not Path(config_path).exists():
    raise RuntimeError(f"BLENDER_CONFIG_PATH not set or not found: {config_path}")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

output_dir = Path(config["output_dir"]) / "smoke_test"
output_dir.mkdir(parents=True, exist_ok=True)

result_path = Path(config["output_dir"]) / "smoke_test_result.json"
width = config.get("width", 640)
height = config.get("height", 360)
engine = config.get("engine", "BLENDER_WORKBENCH")

# Reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Create cube
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "SmokeTestCube"

# Animate the cube rotating
for frame_num in [1, 2, 3]:
    cube.rotation_euler[2] = math.radians(frame_num * 30)
    cube.keyframe_insert(data_path="rotation_euler", frame=frame_num)

# Camera
bpy.ops.object.camera_add(location=(5, -5, 3))
cam = bpy.context.active_object
cam.name = "SmokeCamera"
# Point camera at origin
dx, dy, dz = 0 - 5, 0 - (-5), 0 - 3
cam.rotation_euler = (math.atan2(math.sqrt(dx**2 + dy**2), -dz), 0, math.atan2(dx, dy))
bpy.context.scene.camera = cam

# Sun light
bpy.ops.object.light_add(type="SUN", location=(3, 3, 5))
light = bpy.context.active_object
light.name = "SmokeSun"
light.data.energy = 2.0

# Render settings
scene = bpy.context.scene
scene.render.engine = engine
scene.render.resolution_x = width
scene.render.resolution_y = height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(output_dir / "frame_")
scene.frame_start = 1
scene.frame_end = 3

if engine == "BLENDER_WORKBENCH":
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"

# Render
start = time.time()
frame_times = []
for frame_num in range(1, 4):
    t0 = time.time()
    scene.frame_set(frame_num)
    # Set explicit filepath per frame so each frame gets a unique filename
    scene.render.filepath = str(output_dir / f"frame_{frame_num:04d}")
    bpy.ops.render.render(write_still=True)
    frame_times.append(time.time() - t0)

total_time = time.time() - start
avg_frame = sum(frame_times) / len(frame_times)

result = {
    "frames_rendered": 3,
    "avg_frame_time_s": round(avg_frame, 3),
    "total_time_s": round(total_time, 3),
    "engine": engine,
    "resolution": f"{width}x{height}",
    "success": True
}

with open(result_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)

print(f"SMOKE_TEST_COMPLETE: {json.dumps(result)}")
