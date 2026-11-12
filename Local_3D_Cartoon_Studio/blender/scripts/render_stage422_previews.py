"""
render_stage422_previews.py - Orchestrator for Stage 4.2.2 preview renders.

Plain Python 3.11 script (no top-level bpy).  Runs OUTSIDE Blender and
launches blender.exe as subprocesses, one render job at a time.

Each job writes a small inline Blender script to .agents/tasks/stage422/,
then calls:
    blender --background <blend_file> --python <temp_script>

Usage:
    python render_stage422_previews.py

Outputs 14 PNGs at 640×360 (BLENDER_WORKBENCH) to OUTPUT_DIR.

NEVER overwrites output/stage4_2_1/ or earlier directories.

Prints a final summary table with file sizes and
    RENDER_STAGE422_PREVIEW_OK          — all 14 files > 20 KB
    RENDER_STAGE422_PREVIEW_WARNINGS    — one or more missing / too small
"""

import os
import sys
import subprocess
import textwrap

# ---------------------------------------------------------------------------
# Hardcoded paths
# ---------------------------------------------------------------------------
BLENDER      = r'P:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe'
AARAV_BLEND  = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aarav\aarav_stage4.blend'
AANYA_BLEND  = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aanya\aanya_stage4.blend'
OUTPUT_DIR   = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\output\stage4_2_2\previews'
SCRIPTS_DIR  = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\scripts'
TASKS_DIR    = r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\.agents\tasks\stage422'

# ---------------------------------------------------------------------------
# Safety guard: refuse to overwrite earlier stage previews
# ---------------------------------------------------------------------------
_PROTECTED_DIRS = [
    r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\output\stage4_2_1\previews',
    r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\output\stage4_2\previews',
    r'P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\output\stage4_1\previews',
]

def _check_output_safety():
    out_norm = os.path.normpath(OUTPUT_DIR)
    for protected in _PROTECTED_DIRS:
        if out_norm == os.path.normpath(protected):
            print(f'ERROR: OUTPUT_DIR must not be an earlier stage previews directory: {protected}')
            sys.exit(1)

_check_output_safety()

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Shared Blender script header (emitted at the top of every inline script)
# ---------------------------------------------------------------------------
_HEADER = """\
import sys, os, math
import bpy
import mathutils

SCRIPTS_DIR = {scripts_dir!r}
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from character_movement import (
    compute_rest_offsets,
    apply_action_pose,
    restore_pose,
    setup_workbench,
    make_camera,
)

OUTPUT_DIR = {output_dir!r}
os.makedirs(OUTPUT_DIR, exist_ok=True)

scene = bpy.context.scene
setup_workbench(scene)
"""

def _header():
    return _HEADER.format(scripts_dir=SCRIPTS_DIR, output_dir=OUTPUT_DIR)

# ---------------------------------------------------------------------------
# Helper: write a temp script to TASKS_DIR, run blender, check for RENDER_OK
# ---------------------------------------------------------------------------

def _run_blender(blend_file: str, script_name: str, script_body: str, label: str) -> bool:
    """Write *script_body* to TASKS_DIR/<script_name>, run blender, return True on success."""
    script_path = os.path.join(TASKS_DIR, script_name)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_body)

    cmd = [BLENDER, '--background', blend_file, '--python', script_path]
    print(f'  Running Blender for: {label}')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Print stdout for debugging (suppress huge Blender boot noise, show key lines)
    stdout_lines = result.stdout.splitlines()
    for line in stdout_lines:
        if any(tok in line for tok in ('RENDER_OK', 'WARNING', 'ERROR', 'Rendering', 'Saved')):
            print(f'    [blender] {line}')
    if result.returncode != 0:
        print(f'  ERROR: blender exited {result.returncode} for {label}')
        # Print last 20 lines of stderr for diagnosis
        stderr_lines = result.stderr.splitlines()
        for line in stderr_lines[-20:]:
            print(f'    [stderr] {line}')
        return False

    if 'RENDER_OK' not in result.stdout:
        print(f'  WARNING: RENDER_OK not found in output for {label}')
        # Print last 30 lines for diagnosis
        for line in stdout_lines[-30:]:
            print(f'    [stdout] {line}')
        return False

    return True

# ---------------------------------------------------------------------------
# Single-character render script builder
# ---------------------------------------------------------------------------

_SINGLE_CHAR_TEMPLATE = '''\
{header}
# -- Single character render: {label} --

BLEND_FILE   = {blend_file!r}
CHAR_NAME    = {char_name!r}
ACTION_NAME  = {action_name!r}
FRAME        = {frame}
OUT_FILENAME = {out_filename!r}
FIX_AANYA    = {fix_aanya}

# Camera: single-character — location (0, -4.5, 0.875), look-at (0, 0, 0.875), lens 50mm
cam_pos    = (0.0, -4.5, 0.875)
cam_target = (0.0,  0.0, 0.875)
cam_lens   = 50

arm_obj = bpy.data.objects.get(f'{{CHAR_NAME}}_Armature')
if arm_obj is None:
    print(f'ERROR: {{CHAR_NAME}}_Armature not found in {{BLEND_FILE}}')
    import sys; sys.exit(1)

action = bpy.data.actions.get(ACTION_NAME)
if action is None:
    print(f'ERROR: action {{ACTION_NAME!r}} not found')
    import sys; sys.exit(1)

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

# Compute rest offsets once in rest pose
rest_offsets = compute_rest_offsets(arm_obj, CHAR_NAME)

make_camera(scene, 'RenderCam422', cam_pos, cam_target, cam_lens)

saved = apply_action_pose(arm_obj, ACTION_NAME, FRAME, CHAR_NAME, rest_offsets=rest_offsets)

out_path = os.path.join(OUTPUT_DIR, OUT_FILENAME)
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f'RENDER_OK: {{OUT_FILENAME}}')

restore_pose(arm_obj, saved)
'''

def _build_single_script(char_name, blend_file, action_name, frame, out_filename,
                          fix_aanya=False):
    label = f'{char_name} {action_name} fr{frame} -> {out_filename}'
    return _SINGLE_CHAR_TEMPLATE.format(
        header=_header(),
        label=label,
        blend_file=blend_file,
        char_name=char_name,
        action_name=action_name,
        frame=frame,
        out_filename=out_filename,
        fix_aanya=fix_aanya,
    )

# ---------------------------------------------------------------------------
# Combined-character render script builder
# ---------------------------------------------------------------------------

_COMBINED_TEMPLATE = '''\
{header}
# -- Combined render: {label} --

AARAV_BLEND  = {aarav_blend!r}
AANYA_BLEND  = {aanya_blend!r}
AARAV_ACTION = {aarav_action!r}
AARAV_FRAME  = {aarav_frame}
AANYA_ACTION = {aanya_action!r}
AANYA_FRAME  = {aanya_frame}
OUT_FILENAME = {out_filename!r}
AARAV_X      = {aarav_x}
AANYA_X      = {aanya_x}

# Camera: combined — location (0, -5.5, 0.875), look-at (0, 0, 0.875), lens 40mm
cam_pos    = (0.0, -5.5, 0.875)
cam_target = (0.0,  0.0, 0.875)
cam_lens   = 40

# Append Aanya objects and actions from aanya_stage4.blend
with bpy.data.libraries.load(AANYA_BLEND, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if 'Aanya' in n]
    dst.actions = [n for n in src.actions if 'AANYA' in n]

existing_names = {{o.name for o in scene.collection.objects}}
for obj in bpy.data.objects:
    if obj.name.startswith('Aanya') and obj.name not in existing_names:
        scene.collection.objects.link(obj)

bpy.context.view_layer.update()

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

# Compute rest offsets after orientation/position fixes
aarav_rest = compute_rest_offsets(aarav_arm, 'Aarav')
aanya_rest = compute_rest_offsets(aanya_arm, 'Aanya')

# Apply poses
saved_aarav = {{}}
saved_aanya = {{}}

aa_action = bpy.data.actions.get(AARAV_ACTION)
an_action = bpy.data.actions.get(AANYA_ACTION)

if aa_action:
    saved_aarav = apply_action_pose(aarav_arm, AARAV_ACTION, AARAV_FRAME, 'Aarav',
                                    rest_offsets=aarav_rest)
else:
    print(f'WARNING: action {{AARAV_ACTION!r}} not found')

if an_action:
    saved_aanya = apply_action_pose(aanya_arm, AANYA_ACTION, AANYA_FRAME, 'Aanya',
                                    rest_offsets=aanya_rest)
else:
    print(f'WARNING: action {{AANYA_ACTION!r}} not found')

out_path = os.path.join(OUTPUT_DIR, OUT_FILENAME)
scene.render.filepath = out_path
bpy.ops.render.render(write_still=True)
print(f'RENDER_OK: {{OUT_FILENAME}}')

restore_pose(aarav_arm, saved_aarav)
restore_pose(aanya_arm, saved_aanya)
'''

def _build_combined_script(aarav_action, aarav_frame, aanya_action, aanya_frame,
                            out_filename, aarav_x=-0.6, aanya_x=0.6):
    label = (f'Aarav {aarav_action} fr{aarav_frame} + '
             f'Aanya {aanya_action} fr{aanya_frame} -> {out_filename}')
    return _COMBINED_TEMPLATE.format(
        header=_header(),
        label=label,
        aarav_blend=AARAV_BLEND,
        aanya_blend=AANYA_BLEND,
        aarav_action=aarav_action,
        aarav_frame=aarav_frame,
        aanya_action=aanya_action,
        aanya_frame=aanya_frame,
        out_filename=out_filename,
        aarav_x=aarav_x,
        aanya_x=aanya_x,
    )

# ---------------------------------------------------------------------------
# Main: define all 14 renders and execute
# ---------------------------------------------------------------------------

print('=== RENDER STAGE 4.2.2 PREVIEWS ===')
print(f'Output dir: {OUTPUT_DIR}')
print(f'Tasks dir:  {TASKS_DIR}')
print()

# (render_number, script_name, success) tracking
results = []

def _run_single(n, total, script_name, char_name, blend_file, action_name, frame,
                out_filename, fix_aanya=False):
    label = f'{n}/{total} {out_filename}'
    print(label)
    body = _build_single_script(char_name, blend_file, action_name, frame,
                                 out_filename, fix_aanya=fix_aanya)
    ok = _run_blender(blend_file, script_name, body, out_filename)
    results.append((out_filename, ok))

def _run_combined(n, total, script_name, aarav_action, aarav_frame,
                  aanya_action, aanya_frame, out_filename,
                  aarav_x=-0.6, aanya_x=0.6):
    label = f'{n}/{total} {out_filename}'
    print(label)
    body = _build_combined_script(aarav_action, aarav_frame, aanya_action, aanya_frame,
                                   out_filename, aarav_x=aarav_x, aanya_x=aanya_x)
    ok = _run_blender(AARAV_BLEND, script_name, body, out_filename)
    results.append((out_filename, ok))

# -- Single-character: Aarav --
_run_single(1, 14, 'r01_aarav_idle.py',
            'Aarav', AARAV_BLEND, 'AARAV_IDLE', 1, 'aarav_idle.png')

_run_single(2, 14, 'r02_aarav_wave.py',
            'Aarav', AARAV_BLEND, 'AARAV_WAVE', 6, 'aarav_wave.png')

_run_single(3, 14, 'r03_aarav_point.py',
            'Aarav', AARAV_BLEND, 'AARAV_POINT', 8, 'aarav_point.png')

_run_single(4, 14, 'r04_aarav_nod.py',
            'Aarav', AARAV_BLEND, 'AARAV_NOD', 4, 'aarav_nod.png')

# -- Single-character: Aanya (fix_aanya=True) --
_run_single(5, 14, 'r05_aanya_idle.py',
            'Aanya', AANYA_BLEND, 'AANYA_IDLE', 1, 'aanya_idle.png', fix_aanya=True)

_run_single(6, 14, 'r06_aanya_wave.py',
            'Aanya', AANYA_BLEND, 'AANYA_WAVE', 6, 'aanya_wave.png', fix_aanya=True)

_run_single(7, 14, 'r07_aanya_point.py',
            'Aanya', AANYA_BLEND, 'AANYA_POINT', 8, 'aanya_point.png', fix_aanya=True)

_run_single(8, 14, 'r08_aanya_nod.py',
            'Aanya', AANYA_BLEND, 'AANYA_NOD', 4, 'aanya_nod.png', fix_aanya=True)

# -- Combined renders --
_run_combined(9, 14, 'r09_both_facing_camera.py',
              'AARAV_IDLE', 1,
              'AANYA_IDLE', 1,
              'both_facing_camera.png')

_run_combined(10, 14, 'r10_greeting_interaction.py',
              'AARAV_GREETING', 10,
              'AANYA_GREETING', 10,
              'greeting_interaction.png')

_run_combined(11, 14, 'r11_pointing_interaction.py',
              'AARAV_POINT', 8,
              'AANYA_POINT', 8,
              'pointing_interaction.png')

_run_combined(12, 14, 'r12_walk_together.py',
              'AARAV_WALK', 9,
              'AANYA_WALK', 9,
              'walk_together.png')

# -- Nod sequence representatives (single frame, same as nod.png but labelled as sequence) --
_run_single(13, 14, 'r13_aarav_nod_sequence.py',
            'Aarav', AARAV_BLEND, 'AARAV_NOD', 4, 'aarav_nod_sequence.png')

_run_single(14, 14, 'r14_aanya_nod_sequence.py',
            'Aanya', AANYA_BLEND, 'AANYA_NOD', 4, 'aanya_nod_sequence.png', fix_aanya=True)

# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
print()
print('=== OUTPUT VERIFICATION ===')

EXPECTED = [
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
    'aarav_nod_sequence.png',
    'aanya_nod_sequence.png',
]

all_ok = True
print(f'{"File":<35} {"Size (KB)":>10}  Status')
print('-' * 55)
for fname in EXPECTED:
    fpath = os.path.join(OUTPUT_DIR, fname)
    if os.path.isfile(fpath):
        size_b = os.path.getsize(fpath)
        size_kb = size_b / 1024.0
        status = 'OK' if size_b > 20480 else 'SMALL'
        if size_b <= 20480:
            all_ok = False
        print(f'{fname:<35} {size_kb:>9.1f}  {status}')
    else:
        print(f'{fname:<35} {"MISSING":>10}  MISSING')
        all_ok = False

print()
if all_ok:
    print('RENDER_STAGE422_PREVIEW_OK')
else:
    print('RENDER_STAGE422_PREVIEW_WARNINGS')

sys.exit(0 if all_ok else 1)
