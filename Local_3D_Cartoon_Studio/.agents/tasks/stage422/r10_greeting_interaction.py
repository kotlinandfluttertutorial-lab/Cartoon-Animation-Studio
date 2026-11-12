import sys, os, math
import bpy
import mathutils

SCRIPTS_DIR = 'P:\\AI\\Cartoon-Animation-Studio\\Local_3D_Cartoon_Studio\\blender\\scripts'
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from character_movement import (
    compute_rest_offsets,
    apply_action_pose,
    restore_pose,
    setup_workbench,
    make_camera,
)

OUTPUT_DIR = 'P:\\AI\\Cartoon-Animation-Studio\\Local_3D_Cartoon_Studio\\output\\stage4_2_2\\previews'
os.makedirs(OUTPUT_DIR, exist_ok=True)

scene = bpy.context.scene
setup_workbench(scene)

# -- Combined render: Aarav AARAV_WAVE fr6 + Aanya AANYA_IDLE fr1 -> greeting_interaction.png --

AARAV_BLEND  = 'P:\\AI\\Cartoon-Animation-Studio\\Local_3D_Cartoon_Studio\\blender\\assets\\characters\\aarav\\aarav_stage4.blend'
AANYA_BLEND  = 'P:\\AI\\Cartoon-Animation-Studio\\Local_3D_Cartoon_Studio\\blender\\assets\\characters\\aanya\\aanya_stage4.blend'
AARAV_ACTION = 'AARAV_WAVE'
AARAV_FRAME  = 6
AANYA_ACTION = 'AANYA_IDLE'
AANYA_FRAME  = 1
OUT_FILENAME = 'greeting_interaction.png'
AARAV_X      = -0.6
AANYA_X      = 0.6

# Camera: combined — location (0, +5.5, 0.875), look-at (0, 0, 0.875), lens 40mm
# Camera at +Y looks toward -Y. Aarav faces +Y natively, Aanya has 180deg flip applied.
cam_pos    = (0.0, 5.5, 0.875)
cam_target = (0.0,  0.0, 0.875)
cam_lens   = 40

# Append Aanya objects and actions from aanya_stage4.blend
with bpy.data.libraries.load(AANYA_BLEND, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if 'Aanya' in n]
    dst.actions = [n for n in src.actions if 'AANYA' in n]

existing_names = {o.name for o in scene.collection.objects}
for obj in bpy.data.objects:
    if obj.name.startswith('Aanya') and obj.name not in existing_names:
        scene.collection.objects.link(obj)

bpy.context.view_layer.update()

# Compute Aanya rest offsets BEFORE orientation fix (must be in original rest pose)
aanya_rest = compute_rest_offsets(aanya_arm, 'Aanya')

# Aanya orientation fix: mesh faces -Y, needs 180-degree Z flip
aanya_arm_obj = bpy.data.objects.get('Aanya_Armature')
arm_z = aanya_arm_obj.rotation_euler[2] if aanya_arm_obj else 0.0
for obj in bpy.data.objects:
    if obj.name.startswith('Aanya') and obj.parent is None:
        obj.rotation_euler[2] += math.pi
if abs(arm_z) > 1e-4:
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.parent is None:
            obj.rotation_euler[2] -= arm_z
bpy.context.view_layer.update()
print('  Applied Aanya 180 deg Z rotation (combined render)')

# Position characters: Aarav at X=-0.6, Aanya at X=+0.6
for obj in bpy.data.objects:
    if obj.name.startswith('Aarav') and obj.parent is None:
        obj.location.x = AARAV_X
    elif obj.name.startswith('Aanya') and obj.parent is None:
        obj.location.x = AANYA_X
bpy.context.view_layer.update()

# Camera
make_camera(scene, 'RenderCamBoth422', cam_pos, cam_target, cam_lens)

aarav_arm = bpy.data.objects.get('Aarav_Armature')
aanya_arm = bpy.data.objects.get('Aanya_Armature')

if aarav_arm is None:
    print('ERROR: Aarav_Armature not found')
    import sys; sys.exit(1)
if aanya_arm is None:
    print('ERROR: Aanya_Armature not found')
    import sys; sys.exit(1)

# Compute Aarav rest offsets (after position fix, before any pose)
aarav_rest = compute_rest_offsets(aarav_arm, 'Aarav')
# Aanya rest offsets already computed above (before orientation fix)

# Apply poses
saved_aarav = {}
saved_aanya = {}

aa_action = bpy.data.actions.get(AARAV_ACTION)
an_action = bpy.data.actions.get(AANYA_ACTION)

if aa_action:
    saved_aarav = apply_action_pose(aarav_arm, AARAV_ACTION, AARAV_FRAME, 'Aarav',
                                    rest_offsets=aarav_rest)
else:
    print(f'WARNING: action {AARAV_ACTION!r} not found')

if an_action:
    saved_aanya = apply_action_pose(aanya_arm, AANYA_ACTION, AANYA_FRAME, 'Aanya',
                                    rest_offsets=aanya_rest)
else:
    print(f'WARNING: action {AANYA_ACTION!r} not found')

out_path = os.path.join(OUTPUT_DIR, OUT_FILENAME)
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f'RENDER_OK: {OUT_FILENAME}')

restore_pose(aarav_arm, saved_aarav)
restore_pose(aanya_arm, saved_aanya)
