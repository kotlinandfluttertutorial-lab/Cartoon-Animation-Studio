"""
render_viseme_previews.py — Blender background script.
Applies a specified viseme to a character's mouth object and renders a preview PNG.

Usage:
    blender --background <blend_file> --python render_viseme_previews.py \\
        -- <char_name> <viseme> <output_png>

Prints 'VISEME_PREVIEW_OK' on success.
"""

import sys
import os
import shutil
from datetime import datetime

if "--" not in sys.argv:
    print("ERROR: missing arguments after '--'")
    sys.exit(1)

args = sys.argv[sys.argv.index("--") + 1:]
if len(args) < 3:
    print("ERROR: need <char_name> <viseme> <output_png>")
    sys.exit(1)

char_name = args[0]
viseme = args[1]
output_png = args[2]

import bpy
import mathutils

# Viseme mouth transforms
VISEME_MOUTH_TRANSFORMS = {
    "REST": {"scale": (1.0, 1.0, 1.0), "z_offset":  0.0},
    "MBP":  {"scale": (0.4, 1.0, 0.3), "z_offset":  0.0},
    "FV":   {"scale": (0.6, 1.0, 0.4), "z_offset":  0.0},
    "TD":   {"scale": (0.8, 1.0, 0.6), "z_offset": -0.005},
    "WQ":   {"scale": (0.6, 1.0, 0.8), "z_offset": -0.005},
    "OPEN": {"scale": (1.3, 1.0, 1.4), "z_offset": -0.015},
    "EI":   {"scale": (1.4, 1.0, 0.7), "z_offset":  0.0},
}

# --- Mouth object ---
mouth_obj_name = f"{char_name}_Mouth"
mouth_obj = bpy.data.objects.get(mouth_obj_name)
if mouth_obj is None:
    print(f"ERROR: mouth object '{mouth_obj_name}' not found")
    sys.exit(1)

orig_scale = (float(mouth_obj.scale.x), float(mouth_obj.scale.y), float(mouth_obj.scale.z))
orig_z = float(mouth_obj.location.z)

# Apply viseme transform
tx = VISEME_MOUTH_TRANSFORMS.get(viseme, VISEME_MOUTH_TRANSFORMS["REST"])
sx, sy, sz = tx["scale"]
mouth_obj.scale.x = sx
mouth_obj.scale.y = sy
mouth_obj.scale.z = sz
mouth_obj.location.z = orig_z + tx["z_offset"]
print(f"Applied viseme '{viseme}' to {mouth_obj_name}: scale={tx['scale']} z_offset={tx['z_offset']}")

# --- Scene render setup ---
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

# --- Camera setup ---
cam_pos = (0.0, 4.5, 0.875)
cam_target = (0.0, 0.0, 0.875)

for cam_obj in list(bpy.data.objects):
    if cam_obj.type == "CAMERA":
        bpy.data.objects.remove(cam_obj, do_unlink=True)

cam_data = bpy.data.cameras.new("VisemeCam")
cam_data.lens = 50
cam_obj = bpy.data.objects.new("VisemeCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

cam_obj.location = mathutils.Vector(cam_pos)
direction = mathutils.Vector(cam_target) - mathutils.Vector(cam_pos)
rot_quat = direction.to_track_quat("-Z", "Y")
cam_obj.rotation_euler = rot_quat.to_euler()

# --- Render ---
os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
scene.render.filepath = output_png
bpy.ops.render.render(write_still=True)

# --- Restore mouth ---
mouth_obj.scale.x, mouth_obj.scale.y, mouth_obj.scale.z = orig_scale
mouth_obj.location.z = orig_z

print(f"\n=== VISEME PREVIEW ===")
print(f"Character: {char_name}")
print(f"Viseme   : {viseme}")
print(f"Output   : {output_png}")
print("VISEME_PREVIEW_OK")
sys.exit(0)
