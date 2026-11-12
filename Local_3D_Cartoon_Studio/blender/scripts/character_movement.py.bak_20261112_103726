"""
character_movement.py - Reusable movement, orientation and camera utilities for
Aarav and Aanya in Blender background mode.

Runs INSIDE Blender (import bpy).  Import this module from render scripts that
already have bpy available.

Design notes
------------
* Both characters face +Y at rest (nose at Y ≈ +0.265).
* Bone parenting is OBJECT-type rigid parenting — mesh objects do NOT follow
  bone transforms automatically.  All animation is delivered via Option B:
  apply bone rotations → evaluate depsgraph → move mesh objects to evaluated
  bone midpoints → render → restore.
* The _BONE_TO_MESH mapping is taken verbatim from render_animation_preview.py.
"""

import math
import bpy
import mathutils

# ---------------------------------------------------------------------------
# Bone → mesh suffix mapping
# Taken verbatim from render_animation_preview.py _BONE_TO_MESH
# ---------------------------------------------------------------------------
_BONE_TO_MESH = {
    # Spine chain
    'spine':       ['Spine'],
    'chest':       ['Chest'],
    'neck':        ['Neck'],
    'head':        ['Head'],
    # Arms - Left
    'shoulder_L':  ['Shoulder_L'],
    'upper_arm_L': ['UpperArm_L'],
    'forearm_L':   ['LowerArm_L'],
    'hand_L':      ['Hand_L'],
    # Arms - Right
    'shoulder_R':  ['Shoulder_R'],
    'upper_arm_R': ['UpperArm_R'],
    'forearm_R':   ['LowerArm_R'],
    'hand_R':      ['Hand_R'],
    # Legs - Left
    'thigh_L':     ['UpperLeg_L', 'Thigh_L'],
    'shin_L':      ['LowerLeg_L', 'Shin_L'],
    'foot_L':      ['Foot_L'],
    # Legs - Right
    'thigh_R':     ['UpperLeg_R', 'Thigh_R'],
    'shin_R':      ['LowerLeg_R', 'Shin_R'],
    'foot_R':      ['Foot_R'],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _bone_world_midpoint(arm_eval, bone_name):
    """World-space midpoint of an evaluated pose bone (head+tail)/2."""
    pb = arm_eval.pose.bones.get(bone_name)
    if pb is None:
        return None
    mw = arm_eval.matrix_world
    head_world = mw @ pb.head
    tail_world = mw @ pb.tail
    return (head_world + tail_world) * 0.5


def _apply_pose_from_action(arm_obj, action, frame):
    """
    Sample all rotation_euler fcurves in *action* at *frame* and apply them
    to the pose bones.  Resets all bones to identity first to avoid bleed.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    # Reset all bones
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        pb.location = mathutils.Vector((0.0, 0.0, 0.0))
        pb.scale = mathutils.Vector((1.0, 1.0, 1.0))

    # Apply keyed values
    for fc in action.fcurves:
        if 'rotation_euler' not in fc.data_path:
            continue
        try:
            bone_name = fc.data_path.split('"')[1]
        except IndexError:
            continue
        pb = arm_obj.pose.bones.get(bone_name)
        if pb is None:
            continue
        pb.rotation_mode = 'XYZ'
        val = fc.evaluate(frame)
        pb.rotation_euler[fc.array_index] = val

    bpy.ops.object.mode_set(mode='OBJECT')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def face_direction(arm_obj, char_prefix, direction_vector, mesh_objects=None):
    """
    Rotate the root/hips bone so the character faces *direction_vector*.

    Characters face +Y at rest.  We compute the signed angle between +Y and
    the XY projection of *direction_vector* and apply it as a Z-axis rotation
    on the hips (or root) bone.

    Parameters
    ----------
    arm_obj         : bpy.types.Object  — the character's Armature object
    char_prefix     : str               — 'Aarav' or 'Aanya' (unused here, kept
                                          for API symmetry with other functions)
    direction_vector: sequence of 3 floats — world-space direction to face
    mesh_objects    : unused (kept for API symmetry)
    """
    dv = mathutils.Vector(direction_vector)
    # Project onto XY plane
    dv_xy = mathutils.Vector((dv.x, dv.y, 0.0))
    if dv_xy.length < 1e-6:
        return  # degenerate direction, no rotation

    forward = mathutils.Vector((0.0, 1.0, 0.0))  # +Y is rest forward
    # atan2 gives signed angle from +Y to dv_xy in XY plane
    angle = math.atan2(dv_xy.x, dv_xy.y)  # note: atan2(x,y) not atan2(y,x)

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    # Try 'hips' first, fall back to 'root', 'pelvis', or first bone
    for bone_name in ('hips', 'root', 'pelvis', 'spine'):
        pb = arm_obj.pose.bones.get(bone_name)
        if pb is not None:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler[2] = angle  # Z axis
            break

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()


def face_camera(arm_obj, char_prefix, camera_pos, mesh_objects=None):
    """
    Make the character face toward *camera_pos*.

    Parameters
    ----------
    arm_obj     : bpy.types.Object  — character armature
    char_prefix : str
    camera_pos  : sequence of 3 floats — world position of the camera
    mesh_objects: unused
    """
    # Get character root position
    char_pos = arm_obj.location
    direction = mathutils.Vector(camera_pos) - mathutils.Vector(char_pos)
    face_direction(arm_obj, char_prefix, direction, mesh_objects)


def face_target(arm_obj, char_prefix, target_pos, char_pos, mesh_objects=None):
    """
    Make the character at *char_pos* face toward *target_pos*.

    Parameters
    ----------
    arm_obj     : bpy.types.Object  — character armature
    char_prefix : str
    target_pos  : sequence of 3 floats — world position to face toward
    char_pos    : sequence of 3 floats — world position of the character
    mesh_objects: unused
    """
    direction = mathutils.Vector(target_pos) - mathutils.Vector(char_pos)
    face_direction(arm_obj, char_prefix, direction, mesh_objects)


def move_to(char_objects, target_x, target_y):
    """
    Translate all *root* objects of a character to (target_x, target_y, 0).

    'Root' means objects with no parent (parent is None).  Matches the
    combined-render pattern used in render_animation_preview.py where each
    character's objects are offset by modifying location.x.

    Parameters
    ----------
    char_objects : iterable of bpy.types.Object — all objects belonging to the
                   character (typically filtered by name prefix)
    target_x     : float
    target_y     : float
    """
    for obj in char_objects:
        if obj.parent is None:
            obj.location.x = target_x
            obj.location.y = target_y
            obj.location.z = 0.0
    bpy.context.view_layer.update()


# Bones whose mesh objects we are SAFE to move (arm/leg only).
# Head, Neck, Spine, Chest, Shoulder are excluded to avoid detachment
# in rigid-parenting mode.  NOD gesture applies head bone rotation but
# the head mesh does not visually move in still renders — this is a known
# limitation of Option B with rigid parenting; the rotation is captured
# in bone data and visible in Blender viewport animation playback.
_SAFE_BONES = frozenset({
    'upper_arm_L', 'forearm_L', 'hand_L',
    'upper_arm_R', 'forearm_R', 'hand_R',
    'thigh_L', 'shin_L', 'foot_L',
    'thigh_R', 'shin_R', 'foot_R',
})


def compute_rest_offsets(arm_obj, char_prefix):
    """
    Compute per-object rest-pose offsets: {obj_name: (obj.location - bone_midpoint_in_rest)}.

    Call this ONCE per character in rest pose (all bones at identity) before
    calling apply_action_pose().  Pass the returned dict to apply_action_pose()
    as the `rest_offsets` parameter so mesh objects are repositioned correctly.

    Parameters
    ----------
    arm_obj     : bpy.types.Object  — the character armature
    char_prefix : str               — 'Aarav' or 'Aanya'

    Returns
    -------
    dict  {obj_name: mathutils.Vector}  offset = mesh_origin - rest_bone_midpoint
    """
    # Ensure all bones are at rest pose (identity)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
        pb.location = mathutils.Vector((0.0, 0.0, 0.0))
        pb.scale = mathutils.Vector((1.0, 1.0, 1.0))
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm_obj.evaluated_get(depsgraph)

    offsets = {}
    for bone_name, mesh_suffixes in _BONE_TO_MESH.items():
        midpoint = _bone_world_midpoint(arm_eval, bone_name)
        if midpoint is None:
            continue
        for suffix in mesh_suffixes:
            obj_name = f'{char_prefix}_{suffix}'
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                continue
            offsets[obj_name] = obj.location.copy() - midpoint

    return offsets


def apply_action_pose(arm_obj, action_name, frame, char_prefix,
                      mesh_objects=None, rest_offsets=None):
    """
    Option B: apply the named action at *frame*, move meshes to corrected positions.

    Uses rest_offsets (computed by compute_rest_offsets()) to preserve the
    original spatial relationship between each mesh origin and its bone midpoint.
    If rest_offsets is None, falls back to computing offsets in-place (slower
    but safe for single-frame use).

    Only arm/leg mesh objects are moved (_SAFE_BONES).  Head, Neck, Torso,
    Spine, Chest objects are intentionally excluded to prevent detachment
    in rigid-parenting mode.

    Parameters
    ----------
    arm_obj      : bpy.types.Object  — character armature
    action_name  : str               — action name (e.g. 'AARAV_WAVE')
    frame        : int               — frame to sample
    char_prefix  : str               — 'Aarav' or 'Aanya'
    mesh_objects : unused (kept for API symmetry)
    rest_offsets : dict or None      — from compute_rest_offsets()

    Returns
    -------
    dict  — {obj_name: original_location} for use with restore_pose()
    """
    action = bpy.data.actions.get(action_name)
    if action is None:
        print(f'WARNING: action {action_name!r} not found')
        return {}

    # Step 1: apply bone rotations from action at target frame
    _apply_pose_from_action(arm_obj, action, frame)

    # Step 2: force depsgraph evaluation
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_eval = arm_obj.evaluated_get(depsgraph)

    # Step 2b: if no offsets provided, compute from rest pose (resets+reapplies pose)
    if rest_offsets is None:
        rest_offsets = compute_rest_offsets(arm_obj, char_prefix)
        # Re-apply pose after computing offsets (compute_rest_offsets resets to rest)
        _apply_pose_from_action(arm_obj, action, frame)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        arm_eval = arm_obj.evaluated_get(depsgraph)

    saved = {}

    # Step 3: collect which bones are keyed in this action
    keyed_bones = set()
    for fc in action.fcurves:
        if 'rotation_euler' in fc.data_path:
            try:
                bone_name = fc.data_path.split('"')[1]
                keyed_bones.add(bone_name)
            except IndexError:
                pass

    # Step 4: move only safe (arm/leg) mesh objects with correct offset
    for bone_name in keyed_bones:
        if bone_name not in _SAFE_BONES:
            continue  # skip head, neck, spine, chest — prevents detachment
        mesh_suffixes = _BONE_TO_MESH.get(bone_name, [])
        midpoint = _bone_world_midpoint(arm_eval, bone_name)
        if midpoint is None:
            continue
        for suffix in mesh_suffixes:
            obj_name = f'{char_prefix}_{suffix}'
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                continue
            saved[obj_name] = obj.location.copy()
            # CORRECT: new_position = new_bone_midpoint + rest_offset
            offset = rest_offsets.get(obj_name, mathutils.Vector((0.0, 0.0, 0.0)))
            obj.location = midpoint + offset

    # Step 5: update scene after mesh moves
    bpy.context.view_layer.update()

    return saved


def restore_pose(arm_obj, saved_locations):
    """
    Restore mesh object locations and clear all bone rotations.

    Exact pattern from render_animation_preview.restore_pose().

    Parameters
    ----------
    arm_obj         : bpy.types.Object  — character armature
    saved_locations : dict              — {obj_name: original_location} returned
                                          by apply_action_pose()
    """
    for obj_name, orig_loc in saved_locations.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.location = orig_loc

    if arm_obj is not None:
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='POSE')
        for pb in arm_obj.pose.bones:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
            pb.location = mathutils.Vector((0.0, 0.0, 0.0))
            pb.scale = mathutils.Vector((1.0, 1.0, 1.0))
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.context.view_layer.update()


def setup_workbench(scene):
    """
    Configure scene for Workbench rendering at 640×360 with material colours.

    Parameters
    ----------
    scene : bpy.types.Scene
    """
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


def make_camera(scene, name, pos, target, lens=50):
    """
    Create a camera at *pos* looking at *target* with the given *lens* (mm).

    Uses direction.to_track_quat('-Z', 'Y') for rotation — same as all
    existing render scripts.

    Parameters
    ----------
    scene  : bpy.types.Scene
    name   : str    — camera data/object name
    pos    : (x,y,z) — world position
    target : (x,y,z) — world point the camera looks at
    lens   : float  — focal length in mm (default 50)

    Returns
    -------
    bpy.types.Object  — the camera object (already linked to scene and set as
                         scene.camera)
    """
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_obj = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    cam_obj.location = mathutils.Vector(pos)
    direction = mathutils.Vector(target) - mathutils.Vector(pos)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    return cam_obj
