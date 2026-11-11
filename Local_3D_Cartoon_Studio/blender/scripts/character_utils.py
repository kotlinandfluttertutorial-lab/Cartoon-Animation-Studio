"""
character_utils.py - Shared helpers for cartoon character mesh/rig/material operations.
Runs inside Blender Python (bpy). Compatible with Blender 4.4.3.
"""
import bpy
import math
from mathutils import Vector, Euler


def create_material(name, diffuse_rgba):
    """Create or reuse a material, set diffuse_color and Principled BSDF base color."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    r, g, b, a = diffuse_rgba
    mat.diffuse_color = (r, g, b, a)
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (r, g, b, a)
    return mat


def set_object_color(obj, rgba):
    """Set obj.color for Workbench MATERIAL mode."""
    obj.color = rgba


def add_smooth_shading(obj):
    """Apply smooth shading to all polygons."""
    if obj.type != 'MESH':
        return
    mesh = obj.data
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()


def parent_to_armature(obj, armature):
    """Parent a mesh object to an armature object (OBJECT parenting)."""
    obj.parent = armature
    obj.parent_type = 'OBJECT'


def apply_expression(char_prefix, expression_dict):
    """
    Apply a facial expression by moving/scaling named objects.
    expression_dict: {object_name_suffix: {'location': [dx,dy,dz], 'scale': [sx,sy,sz]}}
    """
    for suffix, transforms in expression_dict.items():
        full_name = f"{char_prefix}_{suffix}"
        obj = bpy.data.objects.get(full_name)
        if obj is None:
            continue
        if 'location' in transforms:
            loc = transforms['location']
            obj.location.x += loc[0]
            obj.location.y += loc[1]
            obj.location.z += loc[2]
        if 'scale' in transforms:
            sc = transforms['scale']
            obj.scale.x = sc[0]
            obj.scale.y = sc[1]
            obj.scale.z = sc[2]


def reset_expression(char_prefix, neutral_state):
    """Reset facial objects to neutral locations/scales."""
    for suffix, transforms in neutral_state.items():
        full_name = f"{char_prefix}_{suffix}"
        obj = bpy.data.objects.get(full_name)
        if obj is None:
            continue
        if 'location' in transforms:
            loc = transforms['location']
            obj.location.x = loc[0]
            obj.location.y = loc[1]
            obj.location.z = loc[2]
        if 'scale' in transforms:
            sc = transforms['scale']
            obj.scale.x = sc[0]
            obj.scale.y = sc[1]
            obj.scale.z = sc[2]


def apply_pose(armature, bone_rotations):
    """
    Apply bone rotations for a pose.
    bone_rotations: {bone_name: (rx, ry, rz)} in radians (Euler XYZ)
    """
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for bone_name, rot in bone_rotations.items():
        pbone = armature.pose.bones.get(bone_name)
        if pbone:
            pbone.rotation_mode = 'XYZ'
            pbone.rotation_euler = Euler(rot, 'XYZ')
    bpy.ops.object.mode_set(mode='OBJECT')


def reset_pose(armature):
    """Reset all pose bones to rest position."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for pbone in armature.pose.bones:
        pbone.rotation_mode = 'XYZ'
        pbone.rotation_euler = Euler((0, 0, 0), 'XYZ')
        pbone.location = Vector((0, 0, 0))
        pbone.scale = Vector((1, 1, 1))
    bpy.ops.object.mode_set(mode='OBJECT')


def count_polygons(collection_name):
    """Count total polygons in all mesh objects in a collection."""
    coll = bpy.data.collections.get(collection_name)
    if coll is None:
        return 0
    total = 0
    for obj in coll.all_objects:
        if obj.type == 'MESH':
            total += len(obj.data.polygons)
    return total


def validate_ground_level(collection_name, tolerance=0.05):
    """Check lowest vertex is at or near z=0."""
    coll = bpy.data.collections.get(collection_name)
    if coll is None:
        return False
    min_z = float('inf')
    for obj in coll.all_objects:
        if obj.type == 'MESH':
            for vert in obj.data.vertices:
                world_co = obj.matrix_world @ vert.co
                if world_co.z < min_z:
                    min_z = world_co.z
    return abs(min_z) <= tolerance


def add_to_collection(obj, collection_name):
    """Ensure object is in named collection, remove from others."""
    coll = bpy.data.collections.get(collection_name)
    if coll is None:
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)
    if obj.name not in [o.name for o in coll.objects]:
        coll.objects.link(obj)
    for c in list(obj.users_collection):
        if c.name != collection_name:
            c.objects.unlink(obj)
