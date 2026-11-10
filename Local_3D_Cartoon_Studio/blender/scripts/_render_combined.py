"""
_render_combined.py - Renders a combined preview with both Aarav and Aanya.
Run via:
    blender --background --factory-startup --python _render_combined.py
"""
import bpy
import math
import mathutils
import os

# 1. Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Append Aarav collection from aarav.blend
aarav_blend = r"P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aarav\aarav.blend"
bpy.ops.wm.append(
    filepath=aarav_blend + r"\Collection\Aarav",
    directory=aarav_blend + r"\Collection\\",
    filename="Aarav"
)

# 3. Append Aanya collection from aanya.blend
aanya_blend = r"P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aanya\aanya.blend"
bpy.ops.wm.append(
    filepath=aanya_blend + r"\Collection\Aanya",
    directory=aanya_blend + r"\Collection\\",
    filename="Aanya"
)

# 4. Move all Aanya objects to X=0.65
aanya_col = bpy.data.collections.get("Aanya")
if aanya_col:
    for obj in aanya_col.all_objects:
        obj.location.x = 0.65

# 5. Move all Aarav objects to X=-0.4
aarav_col = bpy.data.collections.get("Aarav")
if aarav_col:
    for obj in aarav_col.all_objects:
        obj.location.x = -0.4

# 6. Add camera
cam_data = bpy.data.cameras.new("CombinedCam")
cam_data.lens = 50
cam_obj = bpy.data.objects.new("CombinedCam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# Place camera at (0, -4.5, 0.9) looking at (0.1, 0, 0.9)
cam_pos = mathutils.Vector((0, -4.5, 0.9))
target  = mathutils.Vector((0.1, 0, 0.9))
cam_obj.location = cam_pos
direction = target - cam_pos
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

# 7. Configure Workbench render settings
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.film_transparent = False

shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'MATERIAL'
shading.show_shadows = True
shading.show_cavity = True
try:
    shading.show_object_outline = True
except AttributeError:
    pass

# 8. Output path and render
output_dir = r"P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\combined"
os.makedirs(output_dir, exist_ok=True)
scene.render.filepath = output_dir + r"\both_characters.png"
bpy.ops.render.render(write_still=True)

# 9. Signal completion
print("COMBINED_OK")
