"""
Stage 0 — Blender system / GPU / render-engine information probe.
Runs inside Blender: blender --background --factory-startup --python <this>

Writes: output/blender_sysinfo.json
"""

import bpy
import sys
import json
import os
import platform

JSONOUT = os.environ.get(
    "BLENDER_SYSINFO_JSON",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "output", "blender_sysinfo.json"),
)
os.makedirs(os.path.dirname(JSONOUT), exist_ok=True)

# ── Blender version ───────────────────────────────────────────────────────────
ver_str = bpy.app.version_string
exe     = bpy.app.binary_path

# ── Python inside Blender ─────────────────────────────────────────────────────
py_ver = sys.version

# ── Available render engines ──────────────────────────────────────────────────
builtin_engines = []
def _collect_engines(cls):
    for sub in cls.__subclasses__():
        if hasattr(sub, "bl_idname") and sub.bl_idname:
            builtin_engines.append({
                "id":    sub.bl_idname,
                "label": getattr(sub, "bl_label", ""),
            })
        _collect_engines(sub)
_collect_engines(bpy.types.RenderEngine)

# ── Cycles GPU device info ────────────────────────────────────────────────────
cycles_info = {}
try:
    prefs = bpy.context.preferences
    addon_prefs = prefs.addons.get("cycles")
    if addon_prefs:
        cp = addon_prefs.preferences
        default_type = str(cp.compute_device_type)
        all_devices = []
        for dtype in ["CPU", "CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"]:
            try:
                cp.compute_device_type = dtype
                devs = cp.get_devices_for_type(dtype)
                for d in devs:
                    all_devices.append({
                        "name": d.name,
                        "id":   d.id,
                        "use":  d.use,
                        "type": dtype,
                    })
            except Exception as ex:
                pass
        # restore
        try:
            cp.compute_device_type = default_type
        except Exception:
            pass
        cycles_info = {
            "default_compute_device_type": default_type,
            "devices": all_devices,
        }
    else:
        cycles_info = {"note": "cycles addon not found in preferences"}
except Exception as ex:
    cycles_info = {"error": str(ex)}

# ── Build / platform info ─────────────────────────────────────────────────────
build_info = {}
for attr in ["build_platform", "build_type", "build_date", "build_time",
             "build_commit_date", "build_commit_time", "build_hash",
             "build_branch"]:
    val = getattr(bpy.app, attr, None)
    if val is not None:
        build_info[attr] = str(val)

# ── OpenGL renderer (from bpy.app.build_options or wm.opengl_renderer) ───────
opengl_renderer = "unknown"
try:
    # This attribute may not exist in background mode
    opengl_renderer = bpy.context.preferences.system.opengl_renderer
except Exception:
    pass

# ── System platform ───────────────────────────────────────────────────────────
sys_info = {
    "os":           platform.system(),
    "os_release":   platform.release(),
    "os_version":   platform.version(),
    "machine":      platform.machine(),
    "processor":    platform.processor(),
    "python_ver":   py_ver,
}

# ── Compile the report ────────────────────────────────────────────────────────
report = {
    "blender_version":    ver_str,
    "blender_executable": exe,
    "render_engines":     builtin_engines,
    "cycles_gpu":         cycles_info,
    "opengl_renderer":    opengl_renderer,
    "build_info":         build_info,
    "system":             sys_info,
}

with open(JSONOUT, "w") as f:
    json.dump(report, f, indent=2)

print("[Stage0-SysInfo] Blender version : " + ver_str)
print("[Stage0-SysInfo] Executable      : " + exe)
print("[Stage0-SysInfo] Render engines  : " + ", ".join(e["id"] for e in builtin_engines))
print("[Stage0-SysInfo] Cycles devices  : " + json.dumps(cycles_info.get("devices", [])))
print("[Stage0-SysInfo] Written to      : " + JSONOUT)
print("[Stage0-SysInfo] DONE")
