"""
render_stage421_previews.py - Renders 12 Stage 4.2.1 corrected preview PNGs.

Usage:
    blender --background --python render_stage421_previews.py -- <output_dir>

Output (12 PNGs at 640x360 BLENDER_WORKBENCH):
    Single-character (8):
        aarav_idle.png       - Aarav AARAV_IDLE frame 12
        aarav_wave.png       - Aarav AARAV_WAVE frame 6
        aarav_point.png      - Aarav AARAV_POINT frame 8
        aarav_nod.png        - Aarav AARAV_NOD frame 4
        aanya_idle.png       - Aanya AANYA_IDLE frame 12
        aanya_wave.png       - Aanya AANYA_WAVE frame 6
        aanya_point.png      - Aanya AANYA_POINT frame 8
        aanya_nod.png        - Aanya AANYA_NOD frame 4

    Combined (4):
        both_facing_camera.png   - Aarav IDLE fr12, Aanya IDLE fr12
        greeting_interaction.png - Aarav GREETING fr6, Aanya GREETING fr6
        pointing_interaction.png - Aarav POINT fr8, Aanya NOD fr4
        walk_together.png        - Aarav WALK fr1, Aanya WALK fr1

Key fixes vs Stage 4.2:
  - compute_rest_offsets() called once per character before all renders
  - apply_action_pose() uses offset-corrected positioning (midpoint + offset)
  - Only safe arm/leg bones moved; head/neck/spine excluded (_SAFE_BONES)
  - NOD limitation: head mesh doesn't move in still renders (rigid-parenting)

Does NOT overwrite files in output/stage4_2/previews/.

Prints 'RENDER_STAGE421_PREVIEW_OK' on full success, 'RENDER_STAGE421_PREVIEW_WARNINGS' otherwise.
"""

import sys
import os
import math

if '--' in sys.argv:
    args = sys.argv[sys.argv.index('--') + 1:]
else:
    print('Usage: blender --background --python render_stage421_previews.py -- <output_dir>')
    sys.exit(1)

if len(args) < 1:
    print('ERROR: need <output_dir>')
    sys.exit(1)

output_dir = args[0]

# Safety: refuse to overwrite stage4_2 previews
_STAGE42_PREVIEWS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'output', 'stage4_2', 'previews'))
if os.path.normpath(output_dir) == _STAGE42_PREVIEWS:
    print(f'ERROR: output_dir must not be the Stage 4.2 previews directory: {_STAGE42_PREVIEWS}')
    sys.exit(1)

os.makedirs(output_dir, exist_ok=True)

import bpy
import mathutils

# ---------------------------------------------------------------------------
# Import from character_movement
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from character_movement import (
    compute_rest_offsets,
    apply_action_pose,
    restore_pose,
    setup_workbench,
    make_camera,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BLENDER_DIR = os.path.dirname(_SCRIPTS_DIR)
_STUDIO_DIR  = os.path.dirname(_BLENDER_DIR)
_CHARACTERS_DIR = os.path.join(_STUDIO_DIR, 'blender', 'assets', 'characters')

AARAV_BLEND = os.path.join(_CHARACTERS_DIR, 'aarav', 'aarav_stage4.blend')
AANYA_BLEND = os.path.join(_CHARACTERS_DIR, 'aanya', 'aanya_stage4.blend')

for p in [AARAV_BLEND, AANYA_BLEND]:
    if not os.path.isfile(p):
        print(f'ERROR: blend file not found: {p}')
        sys.exit(1)


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------

def setup_scene():
    scene = bpy.context.scene
    setup_workbench(scene)
    return scene


def render_to(scene, filepath):
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------
# Aanya orientation fix (Aanya nose faces -Y, needs 180° flip)
# ---------------------------------------------------------------------------

def fix_aanya_orientation():
    """
    After appending Aanya into a combined scene, ensure Aanya faces +Y.

    Aanya's mesh geometry faces -Y (nose at Y=-0.32 in rest pose, probe confirmed).
    Apply a 180° Z rotation to all parentless Aanya objects so Aanya faces +Y
    (toward the camera). Then also counter-rotate by any additional armature
    Z rotation offset if present.
    """
    aanya_arm = bpy.data.objects.get('Aanya_Armature')
    if aanya_arm is None:
        return

    arm_z_rot = aanya_arm.rotation_euler[2]
    print(f'  Aanya_Armature.rotation_euler[2] = {arm_z_rot:.4f} rad')

    # Always apply 180° flip — mesh faces -Y by design
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.parent is None:
            current_z = obj.rotation_euler[2]
            obj.rotation_euler[2] = current_z + math.pi
    print(f'  Applied 180 deg Z rotation to Aanya objects so face is toward +Y')

    # Also counter-rotate any additional armature Z rotation offset
    if abs(arm_z_rot) > 1e-4:
        for obj in bpy.data.objects:
            if obj.name.startswith('Aanya') and obj.parent is None:
                obj.rotation_euler[2] -= arm_z_rot
        print(f'  Also applied counter-rotation of {-arm_z_rot:.4f} rad')

    bpy.context.view_layer.update()


def fix_aanya_single_orientation():
    """
    In a single-character scene, ensure Aanya faces +Y.

    Probed result: Aanya_Armature has zero rotation_euler but nose is at Y=-0.32,
    meaning the mesh itself faces -Y. Apply a 180° Z rotation to all parentless
    Aanya objects so Aanya faces the camera at +Y.
    """
    aanya_arm = bpy.data.objects.get('Aanya_Armature')
    if aanya_arm is None:
        return

    arm_z_rot = aanya_arm.rotation_euler[2]
    print(f'  Aanya_Armature.rotation_euler[2] = {arm_z_rot:.4f} rad (single scene)')

    # Nose is at Y=-0.32 → mesh faces -Y → needs 180° flip
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.parent is None:
            current_z = obj.rotation_euler[2]
            obj.rotation_euler[2] = current_z + math.pi
    print(f'  Applied 180 deg Z rotation to Aanya objects so face is toward +Y')
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Offset all objects of one character to target X position
# ---------------------------------------------------------------------------

def offset_character(prefix, target_x):
    """Move all parentless objects of *prefix* character to *target_x*."""
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix) and obj.parent is None:
            obj.location.x = target_x
    bpy.context.view_layer.update()


# ===========================================================================
# Single-character render
# ===========================================================================

def render_single(blend_file, char_name, action_name, frame, out_filename,
                  cam_pos=(0, 4.5, 0.875), cam_target=(0, 0, 0.875), lens=50,
                  fix_aanya=False):
    """
    Open blend_file, compute rest offsets once, apply action, render.

    Parameters
    ----------
    blend_file   : str  — path to .blend file
    char_name    : str  — 'Aarav' or 'Aanya'
    action_name  : str  — Blender action name
    frame        : int  — frame to sample
    out_filename : str  — output PNG filename (not full path)
    cam_pos      : tuple  — camera world position
    cam_target   : tuple  — camera look-at point
    lens         : float  — focal length mm
    fix_aanya    : bool  — apply 180° Z flip for Aanya facing
    """
    bpy.ops.wm.open_mainfile(filepath=blend_file)
    scene = setup_scene()

    arm_obj = bpy.data.objects.get(f'{char_name}_Armature')
    if arm_obj is None:
        print(f'WARNING: {char_name}_Armature not found')
        return

    action = bpy.data.actions.get(action_name)
    if action is None:
        print(f'WARNING: action {action_name!r} not found')
        return

    # Fix Aanya orientation before computing rest offsets so offsets match
    # the final orientation
    if fix_aanya:
        fix_aanya_single_orientation()

    # Compute rest offsets ONCE for this character in this scene
    rest_offsets = compute_rest_offsets(arm_obj, char_name)

    make_camera(scene, 'RenderCam', cam_pos, cam_target, lens)

    print(f'  Rendering {action_name} frame {frame} -> {out_filename}')
    saved = apply_action_pose(arm_obj, action_name, frame, char_name,
                              rest_offsets=rest_offsets)
    render_to(scene, os.path.join(output_dir, out_filename))
    restore_pose(arm_obj, saved)


# ===========================================================================
# Combined-character render
# ===========================================================================

def render_combined(aarav_action, aarav_frame,
                    aanya_action, aanya_frame,
                    out_filename,
                    cam_pos=(0.0, 5.5, 0.875), cam_target=(0.0, 0.0, 0.875), lens=40,
                    aarav_x=-0.6, aanya_x=0.6):
    """Load Aarav, append Aanya, apply orientation fix, compute rest offsets, render."""
    bpy.ops.wm.open_mainfile(filepath=AARAV_BLEND)
    scene = setup_scene()

    # Append Aanya objects AND actions
    with bpy.data.libraries.load(AANYA_BLEND, link=False) as (src, dst):
        dst.objects = [name for name in src.objects if 'Aanya' in name]
        dst.actions = [name for name in src.actions if 'AANYA' in name]

    # Link to scene
    existing_names = {o.name for o in scene.collection.objects}
    for obj in bpy.data.objects:
        if obj.name.startswith('Aanya') and obj.name not in existing_names:
            scene.collection.objects.link(obj)

    # Fix Aanya orientation BEFORE computing rest offsets and offsetting X positions
    fix_aanya_orientation()

    # Position characters
    offset_character('Aarav', aarav_x)
    offset_character('Aanya', aanya_x)
    bpy.context.view_layer.update()

    make_camera(scene, 'RenderCamBoth', cam_pos, cam_target, lens)

    aarav_arm = bpy.data.objects.get('Aarav_Armature')
    aanya_arm = bpy.data.objects.get('Aanya_Armature')

    # Compute rest offsets ONCE per character (after orientation and position fixes)
    aarav_rest = compute_rest_offsets(aarav_arm, 'Aarav') if aarav_arm else {}
    aanya_rest = compute_rest_offsets(aanya_arm, 'Aanya') if aanya_arm else {}

    saved_aarav = {}
    saved_aanya = {}

    aa_action = bpy.data.actions.get(aarav_action)
    an_action = bpy.data.actions.get(aanya_action)

    if aarav_arm and aa_action:
        saved_aarav = apply_action_pose(aarav_arm, aarav_action, aarav_frame, 'Aarav',
                                        rest_offsets=aarav_rest)
    elif not aa_action:
        print(f'WARNING: action {aarav_action!r} not found')

    if aanya_arm and an_action:
        saved_aanya = apply_action_pose(aanya_arm, aanya_action, aanya_frame, 'Aanya',
                                        rest_offsets=aanya_rest)
    elif not an_action:
        print(f'WARNING: action {aanya_action!r} not found')

    print(f'  Rendering {out_filename}')
    render_to(scene, os.path.join(output_dir, out_filename))

    if aarav_arm:
        restore_pose(aarav_arm, saved_aarav)
    if aanya_arm:
        restore_pose(aanya_arm, saved_aanya)


# ===========================================================================
# Main render sequence
# ===========================================================================

print('=== RENDER STAGE 4.2.1 PREVIEWS ===')
print(f'Output dir: {output_dir}')

# ---------------------------------------------------------------------------
# Single-character: Aarav (8 total, 4 Aarav)
# ---------------------------------------------------------------------------

print('1/12 aarav_idle.png')
render_single(AARAV_BLEND, 'Aarav', 'AARAV_IDLE', 12, 'aarav_idle.png')

print('2/12 aarav_wave.png')
render_single(AARAV_BLEND, 'Aarav', 'AARAV_WAVE', 6, 'aarav_wave.png')

print('3/12 aarav_point.png')
render_single(AARAV_BLEND, 'Aarav', 'AARAV_POINT', 8, 'aarav_point.png')

print('4/12 aarav_nod.png  (NOD: head bone rotates; head mesh stays — rigid-parenting limitation)')
render_single(AARAV_BLEND, 'Aarav', 'AARAV_NOD', 4, 'aarav_nod.png')

# ---------------------------------------------------------------------------
# Single-character: Aanya (fix_aanya=True — mesh faces -Y, needs 180° flip)
# ---------------------------------------------------------------------------

print('5/12 aanya_idle.png')
render_single(AANYA_BLEND, 'Aanya', 'AANYA_IDLE', 12, 'aanya_idle.png', fix_aanya=True)

print('6/12 aanya_wave.png')
render_single(AANYA_BLEND, 'Aanya', 'AANYA_WAVE', 6, 'aanya_wave.png', fix_aanya=True)

print('7/12 aanya_point.png')
render_single(AANYA_BLEND, 'Aanya', 'AANYA_POINT', 8, 'aanya_point.png', fix_aanya=True)

print('8/12 aanya_nod.png  (NOD: head bone rotates; head mesh stays — rigid-parenting limitation)')
render_single(AANYA_BLEND, 'Aanya', 'AANYA_NOD', 4, 'aanya_nod.png', fix_aanya=True)

# ---------------------------------------------------------------------------
# Combined renders (4)
# ---------------------------------------------------------------------------

print('9/12 both_facing_camera.png')
render_combined(
    'AARAV_IDLE', 12,
    'AANYA_IDLE', 12,
    'both_facing_camera.png',
)

print('10/12 greeting_interaction.png')
render_combined(
    'AARAV_GREETING', 6,
    'AANYA_GREETING', 6,
    'greeting_interaction.png',
)

print('11/12 pointing_interaction.png')
render_combined(
    'AARAV_POINT', 8,
    'AANYA_NOD', 4,
    'pointing_interaction.png',
)

print('12/12 walk_together.png')
render_combined(
    'AARAV_WALK', 1,
    'AANYA_WALK', 1,
    'walk_together.png',
)

# ---------------------------------------------------------------------------
# Verify outputs
# ---------------------------------------------------------------------------
print()
print('=== OUTPUT VERIFICATION ===')
expected = [
    'aarav_idle.png',
    'aarav_wave.png',
    'aarav_point.png',
    'aarav_nod.png',
    'aanya_idle.png',
    'aanya_wave.png',
    'aanya_point.png',
    'aanya_nod.png',
    'both_facing_camera.png',
    'greeting_interaction.png',
    'pointing_interaction.png',
    'walk_together.png',
]

all_ok = True
for fname in expected:
    fpath = os.path.join(output_dir, fname)
    if os.path.isfile(fpath):
        size = os.path.getsize(fpath)
        status = 'OK' if size > 20480 else 'SMALL'
        print(f'  {fname}: {size} bytes [{status}]')
        if size <= 20480:
            all_ok = False
    else:
        print(f'  {fname}: MISSING')
        all_ok = False

print()
if all_ok:
    print('RENDER_STAGE421_PREVIEW_OK')
else:
    print('RENDER_STAGE421_PREVIEW_WARNINGS')

sys.exit(0)
