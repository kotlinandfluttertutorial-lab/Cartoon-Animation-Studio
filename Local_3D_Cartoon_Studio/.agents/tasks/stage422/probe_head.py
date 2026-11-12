"""
probe_head.py — Stage 4.2.2 investigator
Runs inside Blender: blender --background <blend_file> --python probe_head.py -- <blend_file> <char_prefix>
Outputs JSON to stdout lines starting with PROBE_RESULT:
"""
import sys, json, math
import bpy, mathutils

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    args = []

blend_file = args[0]
char_prefix = args[1]  # 'Aarav' or 'Aanya'

bpy.ops.wm.open_mainfile(filepath=blend_file)

arm_name = f'{char_prefix}_Armature'
arm_obj = bpy.data.objects.get(arm_name)

result = {
    'char': char_prefix,
    'armature_location': list(arm_obj.location) if arm_obj else None,
    'head_mesh': None,
    'neck_mesh': None,
    'hijab_mesh': None,
    'head_bone': None,
    'neck_bone': None,
}

if arm_obj:
    # Reset all bones to rest pose
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler((0, 0, 0), 'XYZ')
        pb.location = mathutils.Vector((0, 0, 0))
        pb.scale = mathutils.Vector((1, 1, 1))
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm_obj.evaluated_get(depsgraph)

    for bone_name in ('head', 'neck'):
        pb = arm_eval.pose.bones.get(bone_name)
        if pb:
            mw = arm_eval.matrix_world
            h = list(mw @ pb.head)
            t = list(mw @ pb.tail)
            mid = [(h[i]+t[i])/2 for i in range(3)]
            result[f'{bone_name}_bone'] = {'head': h, 'tail': t, 'midpoint': mid}

    for suffix in ('Head', 'Neck', 'Hijab'):
        obj_name = f'{char_prefix}_{suffix}'
        obj = bpy.data.objects.get(obj_name)
        if obj:
            parent_name = obj.parent.name if obj.parent else None
            parent_bone = obj.parent_bone if obj.parent_bone else None
            result[f'{suffix.lower()}_mesh'] = {
                'name': obj_name,
                'location': list(obj.location),
                'dimensions': list(obj.dimensions),
                'parent': parent_name,
                'parent_bone': parent_bone,
                'parent_type': obj.parent_type,
            }

print('PROBE_RESULT:' + json.dumps(result))
print('PROBE_DONE')
