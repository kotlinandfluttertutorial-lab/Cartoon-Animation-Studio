"""
render_character_preview.py - Renders preview images for a character .blend file.

Usage:
    blender --background --factory-startup --python render_character_preview.py -- <character_name> <blend_file> <output_dir>
"""
import sys
import os

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background --python render_character_preview.py -- <character_name> <blend_file> <output_dir>')
    sys.exit(1)

character_name = args[0]
blend_file = args[1]
output_dir = args[2]

# Add scripts directory to sys.path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

import bpy
import mathutils
import math
import json

os.makedirs(output_dir, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend_file)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.film_transparent = False

# Configure display shading for background render
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'MATERIAL'
shading.show_shadows = True
shading.show_cavity = True
try:
    shading.show_object_outline = True
except AttributeError:
    pass

# ---------------------------------------------------------------------------
# Camera helper
# ---------------------------------------------------------------------------
def set_camera(cam_obj, pos, target):
    cam_obj.location = pos
    direction = mathutils.Vector(target) - mathutils.Vector(pos)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

# ---------------------------------------------------------------------------
# Create camera
# ---------------------------------------------------------------------------
cam_data = bpy.data.cameras.new('RenderCam')
cam_data.lens = 50
cam_obj = bpy.data.objects.new('RenderCam', cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# ---------------------------------------------------------------------------
# Render helper
# ---------------------------------------------------------------------------
def render_to(filepath):
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------------------
# Find armature
# ---------------------------------------------------------------------------
arm_obj = bpy.data.objects.get(f'{character_name}_Armature')

# ---------------------------------------------------------------------------
# Pose helpers
# ---------------------------------------------------------------------------
def apply_wave_pose():
    if arm_obj is None:
        return
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for bname, rot in [('upper_arm_R', (-1.2, 0, 0)), ('forearm_R', (-0.5, 0, 0))]:
        pb = arm_obj.pose.bones.get(bname)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = rot
    bpy.ops.object.mode_set(mode='OBJECT')

def reset_wave_pose():
    if arm_obj is None:
        return
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for bname in ['upper_arm_R', 'forearm_R']:
        pb = arm_obj.pose.bones.get(bname)
        if pb:
            from mathutils import Euler
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = Euler((0, 0, 0), 'XYZ')
    bpy.ops.object.mode_set(mode='OBJECT')

def apply_happy_expression():
    prefix = character_name
    for suffix, sc in [('Mouth', (1.1, 1.0, 0.8)), ('Eye_L', (1.0, 1.0, 0.75)), ('Eye_R', (1.0, 1.0, 0.75))]:
        obj = bpy.data.objects.get(f'{prefix}_{suffix}')
        if obj:
            obj.scale = sc

def reset_happy_expression():
    prefix = character_name
    for suffix in ['Mouth', 'Eye_L', 'Eye_R']:
        obj = bpy.data.objects.get(f'{prefix}_{suffix}')
        if obj:
            obj.scale = (1.0, 1.0, 1.0)

# ---------------------------------------------------------------------------
# Render all 5 views
# ---------------------------------------------------------------------------
target = (0, 0, 0.9)

# front
set_camera(cam_obj, (0, -3.5, 0.9), target)
render_to(os.path.join(output_dir, 'front.png'))

# side
set_camera(cam_obj, (3.5, 0, 0.9), target)
render_to(os.path.join(output_dir, 'side.png'))

# three_quarter
set_camera(cam_obj, (2.5, -2.5, 0.9), target)
render_to(os.path.join(output_dir, 'three_quarter.png'))

# wave_pose
apply_wave_pose()
set_camera(cam_obj, (0, -3.5, 0.9), target)
render_to(os.path.join(output_dir, 'wave_pose.png'))
reset_wave_pose()

# happy_expression
apply_happy_expression()
set_camera(cam_obj, (0, -3.5, 0.9), target)
render_to(os.path.join(output_dir, 'happy_expression.png'))
reset_happy_expression()

print('RENDER_COMPLETE')
sys.exit(0)
