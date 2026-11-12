"""
apply_expression.py — Blender background script for expression preview rendering.

Applies a single facial expression to a character and renders a preview PNG.

Usage:
    blender --background <blend_file> --python apply_expression.py \\
        -- <char_name> <emotion> <output_png>

Arguments after '--':
    char_name  : 'Aarav' or 'Aanya'
    emotion    : one of neutral, happy, surprised, sad, thinking, excited
    output_png : path to write the rendered PNG

Prints 'EXPRESSION_RENDER_OK' on success.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
if "--" not in sys.argv:
    print("ERROR: missing arguments after '--'")
    sys.exit(1)

args = sys.argv[sys.argv.index("--") + 1:]
if len(args) < 3:
    print("ERROR: need <char_name> <emotion> <output_png>")
    sys.exit(1)

char_name = args[0]   # 'Aarav' or 'Aanya'
emotion = args[1]
output_png = args[2]

import bpy
import mathutils

# ---------------------------------------------------------------------------
# Expression definitions (mirrors expression_library.py)
# ---------------------------------------------------------------------------
EXPRESSIONS = {
    "neutral": {},

    "happy": {
        "Eyebrow_L": {"z_offset": +0.025},
        "Eyebrow_R": {"z_offset": +0.025},
        "Mouth":     {"scale": (1.2, 1.0, 0.7)},
    },

    "surprised": {
        "Eyebrow_L": {"z_offset": +0.04},
        "Eyebrow_R": {"z_offset": +0.04},
        "Eye_L":     {"scale": (1.0, 1.0, 1.3)},
        "Eye_R":     {"scale": (1.0, 1.0, 1.3)},
        "Mouth":     {"scale": (1.3, 1.0, 1.3)},
    },

    "sad": {
        "Eyebrow_L": {"z_offset": -0.02},
        "Eyebrow_R": {"z_offset": -0.02},
        "Mouth":     {"scale": (0.9, 1.0, 0.8)},
    },

    "thinking": {
        "Eyebrow_R": {"z_offset": +0.02},
    },

    "excited": {
        "Eyebrow_L": {"z_offset": +0.03},
        "Eyebrow_R": {"z_offset": +0.03},
        "Mouth":     {"scale": (1.3, 1.0, 1.1)},
    },
}

# ---------------------------------------------------------------------------
# Apply expression to character objects
# ---------------------------------------------------------------------------
transforms = EXPRESSIONS.get(emotion, {})
saved_state: dict[str, dict] = {}

for suffix, tx in transforms.items():
    obj_name = f"{char_name}_{suffix}"
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        print(f"  SKIP: object '{obj_name}' not found in scene")
        continue

    # Save originals
    saved_state[obj_name] = {
        "original_z":     float(obj.location.z),
        "original_scale": (float(obj.scale.x), float(obj.scale.y), float(obj.scale.z)),
    }

    # Apply z_offset
    if "z_offset" in tx:
        obj.location.z += tx["z_offset"]

    # Apply scale
    if "scale" in tx:
        sx, sy, sz = tx["scale"]
        obj.scale.x *= sx
        obj.scale.y *= sy
        obj.scale.z *= sz

    print(f"  Applied {emotion} to {obj_name}")

# ---------------------------------------------------------------------------
# Scene / render setup
# ---------------------------------------------------------------------------
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.film_transparent = False

shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "MATERIAL"
shading.show_shadows = True
shading.show_cavity = True
try:
    shading.show_object_outline = True
except AttributeError:
    pass

# Camera: position at (0, 4.5, 0.875) looking at (0, 0, 0.875), lens 50mm
cam_pos = (0.0, 4.5, 0.875)
cam_target = (0.0, 0.0, 0.875)

# Remove existing cameras
for cam_obj in list(bpy.data.objects):
    if cam_obj.type == "CAMERA":
        bpy.data.objects.remove(cam_obj, do_unlink=True)

cam_data = bpy.data.cameras.new("ExpressionCam")
cam_data.lens = 50
cam_obj = bpy.data.objects.new("ExpressionCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

cam_obj.location = mathutils.Vector(cam_pos)
direction = mathutils.Vector(cam_target) - mathutils.Vector(cam_pos)
rot_quat = direction.to_track_quat("-Z", "Y")
cam_obj.rotation_euler = rot_quat.to_euler()

# Output path
os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
scene.render.filepath = output_png
bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------------------
# Restore objects after render
# ---------------------------------------------------------------------------
for obj_name, state in saved_state.items():
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        continue
    obj.location.z = state["original_z"]
    sx, sy, sz = state["original_scale"]
    obj.scale.x = sx
    obj.scale.y = sy
    obj.scale.z = sz

print(f"\n=== EXPRESSION RENDER SUMMARY ===")
print(f"Character : {char_name}")
print(f"Emotion   : {emotion}")
print(f"Output    : {output_png}")
print("EXPRESSION_RENDER_OK")
sys.exit(0)
