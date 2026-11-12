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

# -- Single character render: Aanya AANYA_NOD fr4 -> aanya_nod_sequence.png --

BLEND_FILE   = 'P:\\AI\\Cartoon-Animation-Studio\\Local_3D_Cartoon_Studio\\blender\\assets\\characters\\aanya\\aanya_stage4.blend'
CHAR_NAME    = 'Aanya'
ACTION_NAME  = 'AANYA_NOD'
FRAME        = 4
OUT_FILENAME = 'aanya_nod_sequence.png'
FIX_AANYA    = False

# Camera: single-character — location (0, +4.5, 0.875), look-at (0, 0, 0.875), lens 50mm
# Aarav nose is at Y=+0.265 (face on +Y side). Camera at +Y looks toward -Y, sees the front.
# Aanya nose is at Y=-0.320 (face on -Y side). FIX_AANYA rotates her 180deg so she also faces +Y.
cam_pos    = (0.0, -4.5, 0.875)
cam_target = (0.0,  0.0, 0.875)
cam_lens   = 50

arm_obj = bpy.data.objects.get(f'{CHAR_NAME}_Armature')
if arm_obj is None:
    print(f'ERROR: {CHAR_NAME}_Armature not found in {BLEND_FILE}')
    import sys; sys.exit(1)

action = bpy.data.actions.get(ACTION_NAME)
if action is None:
    print(f'ERROR: action {ACTION_NAME!r} not found')
    import sys; sys.exit(1)

# Compute rest offsets BEFORE orientation fix (must be in original rest pose)
rest_offsets = compute_rest_offsets(arm_obj, CHAR_NAME)

# Aanya orientation fix: mesh faces -Y, needs 180-degree Z flip
if FIX_AANYA:
    aanya_arm = bpy.data.objects.get('Aanya_Armature')
    arm_z = aanya_arm.rotation_euler[2] if aanya_arm else 0.0
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.parent is None:
            obj.rotation_euler[2] += math.pi
    if abs(arm_z) > 1e-4:
        for obj in bpy.data.objects:
            if obj.name.startswith('Aanya') and obj.parent is None:
                obj.rotation_euler[2] -= arm_z
    bpy.context.view_layer.update()
    print(f'  Applied 180 deg Z rotation to Aanya objects')

make_camera(scene, 'RenderCam422', cam_pos, cam_target, cam_lens)

saved = apply_action_pose(arm_obj, ACTION_NAME, FRAME, CHAR_NAME, rest_offsets=rest_offsets)

out_path = os.path.join(OUTPUT_DIR, OUT_FILENAME)
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f'RENDER_OK: {OUT_FILENAME}')

restore_pose(arm_obj, saved)
