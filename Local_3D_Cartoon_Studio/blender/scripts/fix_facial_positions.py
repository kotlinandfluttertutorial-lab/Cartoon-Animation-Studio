"""
fix_facial_positions.py  –  Stage 2.1 Fix 5: Facial Feature Visibility

Root cause: facial feature mesh objects were placed at Y = +0.24..+0.265 (facing +Y),
but the front preview camera is at Y = -3.5 and looks in the +Y direction, so it sees
the BACK of the head.  The head sphere is centred at (0, 0, 1.4) with scale 0.28,
giving a front surface at approximately Y = -0.28.  All facial meshes must sit on the
-Y hemisphere (Y < -0.28) to be visible from the front camera.

Fix: negate the Y coordinate of every facial feature object and push it 0.015–0.02 BU
further in -Y so it clears the head surface.

Affected objects in BOTH blend files
  Aarav_Eye_L, Aarav_Eye_R        Y: +0.240 → -0.265
  Aarav_Iris_L, Aarav_Iris_R      Y: +0.265 → -0.278
  Aarav_Eyebrow_L, Aarav_Eyebrow_R Y: +0.250 → -0.265
  Aarav_Nose                       Y: +0.265 → -0.278
  Aarav_Mouth                      Y: +0.250 → -0.265
  (identical offsets for Aanya_*)

Usage:
    blender --background --factory-startup --python fix_facial_positions.py
"""
import bpy
import os
import time
import shutil

BLENDER_EXE = r"P:\AI\Cartoon-Animation-Studio\tools\blender-4.4.3-windows-x64\blender.exe"

CHARACTERS = [
    {
        "id":      "aarav",
        "prefix":  "Aarav",
        "blend":   r"P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aarav\aarav.blend",
    },
    {
        "id":      "aanya",
        "prefix":  "Aanya",
        "blend":   r"P:\AI\Cartoon-Animation-Studio\Local_3D_Cartoon_Studio\blender\assets\characters\aanya\aanya.blend",
    },
]

# Suffix → new Y value.
# X and Z positions are preserved exactly from the original create_*.py values.
# Head sphere centre (0, 0, 1.4), scale 0.28 → front surface at Y ≈ -0.28.
# Each facial object is pushed a further ~0.01–0.02 BU past the surface.
FACIAL_Y_FIX = {
    "Eye_L":      -0.265,   # eye-white sphere (scale Y 0.03); surface clears head by ~0.015 BU
    "Eye_R":      -0.265,
    "Iris_L":     -0.278,   # iris is 0.015 BU proud of the eye white
    "Iris_R":     -0.278,
    "Eyebrow_L":  -0.265,   # eyebrow cube, flush with head surface
    "Eyebrow_R":  -0.265,
    "Nose":       -0.278,   # nose sphere protrudes 0.025 BU in Y scale; tip at -0.278
    "Mouth":      -0.265,   # mouth cube, flush with head surface
}


def fix_character(char_info):
    blend_path = char_info["blend"]
    prefix     = char_info["prefix"]
    char_id    = char_info["id"]

    print(f"\n[Fix5] Processing {prefix} ({blend_path})")

    # --- Backup ---------------------------------------------------------
    backup_path = blend_path + f".fix5_{int(time.time())}.bak"
    shutil.copy2(blend_path, backup_path)
    print(f"[Fix5]   Backed up to: {backup_path}")

    # --- Load -----------------------------------------------------------
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    # --- Apply fixes ----------------------------------------------------
    changed = []
    skipped = []

    for suffix, new_y in FACIAL_Y_FIX.items():
        obj_name = f"{prefix}_{suffix}"
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            skipped.append(obj_name)
            print(f"[Fix5]   SKIP (not found): {obj_name}")
            continue

        old_y = obj.location.y
        obj.location.y = new_y
        changed.append((obj_name, old_y, new_y))
        print(f"[Fix5]   {obj_name}: Y {old_y:+.4f} → {new_y:+.4f}")

    if skipped:
        print(f"[Fix5]   WARNING: {len(skipped)} objects not found: {skipped}")

    # --- Save -----------------------------------------------------------
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[Fix5]   Saved: {blend_path}")

    return {"changed": changed, "skipped": skipped}


# Run for both characters
results = {}
for char in CHARACTERS:
    results[char["id"]] = fix_character(char)

print("\n[Fix5] === SUMMARY ===")
for char_id, r in results.items():
    print(f"  {char_id}: {len(r['changed'])} objects moved, {len(r['skipped'])} skipped")
print("[Fix5] FACIAL_FIX_COMPLETE")
