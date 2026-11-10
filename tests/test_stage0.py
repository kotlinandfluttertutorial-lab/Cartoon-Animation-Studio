"""
Stage 0 — Blender detection and rendering integration tests.
Run with: python tests/test_stage0.py

Tests:
  1. Blender executable exists and is correct version
  2. Blender background mode + Python scripting works
  3. Workbench renders at least 1 frame successfully
  4. FFmpeg exists and can mux frames to MP4
  5. Render timing JSON is valid and meets minimum performance thresholds
"""

import os
import sys
import json
import subprocess
import time
import tempfile
import shutil
import unittest

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS    = os.path.join(ROOT, "tools")
SCRIPTS  = os.path.join(ROOT, "scripts")
OUTPUT   = os.path.join(ROOT, "output")

BLENDER  = os.path.join(TOOLS, "blender-4.4.3-windows-x64", "blender.exe")
FFMPEG_PATH = (
    r"C:\Users\admin\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
)
# Fallback: check PATH
if not os.path.isfile(FFMPEG_PATH):
    import shutil as _sh
    _found = _sh.which("ffmpeg")
    if _found:
        FFMPEG_PATH = _found

WB_TIMING_JSON = os.path.join(OUTPUT, "render_timing_workbench.json")


# ─────────────────────────────────────────────────────────────────────────────
class TestBlenderDetection(unittest.TestCase):
    """Task 1 & 9 — Blender executable detection."""

    def test_blender_executable_exists(self):
        self.assertTrue(
            os.path.isfile(BLENDER),
            f"blender.exe not found at: {BLENDER}"
        )

    def test_blender_version(self):
        result = subprocess.run(
            [BLENDER, "--version"],
            capture_output=True, text=True, timeout=15
        )
        self.assertEqual(result.returncode, 0, "blender --version failed")
        self.assertIn("4.4", result.stdout, "Expected Blender 4.4.x")
        print(f"  Blender version output: {result.stdout.splitlines()[0]}")

    def test_blender_background_python(self):
        """Verify --background --python mode works with a trivial script."""
        script = "import bpy; print('BPY_OK:', bpy.app.version_string)"
        result = subprocess.run(
            [BLENDER, "--background", "--factory-startup", "--python-expr", script],
            capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, f"Background Python failed:\n{result.stderr}")
        self.assertIn("BPY_OK:", result.stdout, "bpy import failed")
        print(f"  Python expr output: {[l for l in result.stdout.splitlines() if 'BPY_OK' in l]}")


# ─────────────────────────────────────────────────────────────────────────────
class TestBlenderRendering(unittest.TestCase):
    """Task 3 & 7 — Single-frame Workbench render test."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="stage0_test_")
        cls.json_out = os.path.join(cls.tmp_dir, "timing.json")

        # Minimal render script: 1 frame only
        cls.mini_script = os.path.join(cls.tmp_dir, "mini_render.py")
        with open(cls.mini_script, "w") as f:
            f.write(f"""\
import bpy, os, json, time, math

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.resolution_x = 320
scene.render.resolution_y = 180
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.image_settings.file_format = "PNG"

bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
cam_data = bpy.data.cameras.new("C"); cam_obj = bpy.data.objects.new("C", cam_data)
scene.collection.objects.link(cam_obj); cam_obj.location=(0,-5,2)
cam_obj.rotation_euler=(math.radians(70),0,0); scene.camera=cam_obj
import math

t0 = time.perf_counter()
scene.frame_set(1)
bpy.ops.render.render(write_still=False)
out_path = os.path.join(r"{cls.tmp_dir}", "frame_test.png")
bpy.data.images["Render Result"].save_render(out_path)
elapsed = time.perf_counter() - t0

result = {{"frames_rendered": 1, "frame_time_s": round(elapsed,3),
           "output_path": out_path, "output_exists": os.path.isfile(out_path)}}
with open(r"{cls.json_out}", "w") as fh: import json; json.dump(result, fh)
print("[mini] done", result)
""")

        env = os.environ.copy()
        cls.proc = subprocess.run(
            [BLENDER, "--background", "--factory-startup", "--python", cls.mini_script],
            capture_output=True, text=True, timeout=120, env=env
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_render_exit_code(self):
        self.assertEqual(self.proc.returncode, 0,
                         f"Blender render exited {self.proc.returncode}:\n{self.proc.stderr[-2000:]}")

    def test_frame_was_saved(self):
        if not os.path.isfile(self.json_out):
            self.skipTest("Timing JSON not written — render likely failed")
        data = json.load(open(self.json_out))
        self.assertTrue(data.get("output_exists"), "Frame PNG was not saved")

    def test_frame_time_reasonable(self):
        if not os.path.isfile(self.json_out):
            self.skipTest("Timing JSON not written")
        data = json.load(open(self.json_out))
        t = data.get("frame_time_s", 9999)
        # Workbench should render 320x180 in under 10 seconds on any modern CPU
        self.assertLess(t, 10.0, f"Frame took {t}s — unexpectedly slow for Workbench")
        print(f"  Workbench 320x180 frame time: {t}s OK")


# ─────────────────────────────────────────────────────────────────────────────
class TestWorkbenchTimingReport(unittest.TestCase):
    """Task 7 — Validate the full 60-frame Workbench benchmark results."""

    def test_timing_json_exists(self):
        self.assertTrue(os.path.isfile(WB_TIMING_JSON),
                        f"Workbench timing JSON not found: {WB_TIMING_JSON}")

    def test_timing_json_valid(self):
        with open(WB_TIMING_JSON) as f:
            data = json.load(f)
        self.assertEqual(data["engine"], "WORKBENCH")
        self.assertEqual(data["total_frames"], 60)
        self.assertEqual(data["frames_rendered"], 60, "Not all 60 frames were rendered")
        print(f"  total_render_time_s : {data['total_render_time_s']}")
        print(f"  avg_frame_time_s    : {data['avg_frame_time_s']}")
        print(f"  total_output_mb     : {data['total_output_mb']}")

    def test_workbench_speed(self):
        """Workbench should render 60 frames at 640x360 in under 60 seconds."""
        with open(WB_TIMING_JSON) as f:
            data = json.load(f)
        t = data["total_render_time_s"]
        self.assertLess(t, 60.0,
                        f"Workbench took {t}s for 60 frames — too slow (expected <60s)")

    def test_all_frames_present(self):
        frames_dir = os.path.join(OUTPUT, "frames", "wb2")
        if not os.path.isdir(frames_dir):
            self.skipTest("wb2 frames directory not found")
        pngs = [f for f in os.listdir(frames_dir) if f.endswith(".png")]
        self.assertEqual(len(pngs), 60, f"Expected 60 PNGs, found {len(pngs)}")


# ─────────────────────────────────────────────────────────────────────────────
class TestFFmpeg(unittest.TestCase):
    """Task 8 — FFmpeg frame-to-MP4 conversion test."""

    def test_ffmpeg_exists(self):
        self.assertTrue(
            os.path.isfile(FFMPEG_PATH),
            f"ffmpeg not found at: {FFMPEG_PATH}"
        )

    def test_ffmpeg_version(self):
        result = subprocess.run(
            [FFMPEG_PATH, "-version"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ffmpeg version", result.stdout)
        ver_line = result.stdout.splitlines()[0]
        print(f"  {ver_line}")

    def test_mp4_output_exists(self):
        mp4 = os.path.join(OUTPUT, "video", "stage0_test.mp4")
        self.assertTrue(os.path.isfile(mp4), f"MP4 not found: {mp4}")
        size = os.path.getsize(mp4)
        self.assertGreater(size, 1000, "MP4 file is too small — likely corrupted")
        print(f"  MP4 size: {size/1024:.1f} KB")

    def test_ffmpeg_mux_from_frames(self):
        """Mux 5 frames into a test MP4 to verify FFmpeg pipeline works."""
        frames_dir = os.path.join(OUTPUT, "frames", "wb2")
        if not os.path.isdir(frames_dir):
            self.skipTest("wb2 frames directory not found")

        tmp_out = os.path.join(OUTPUT, "video", "_test_mux.mp4")
        result = subprocess.run(
            [FFMPEG_PATH, "-y",
             "-framerate", "12",
             "-start_number", "1",
             "-i", os.path.join(frames_dir, "frame_%04d.png"),
             "-frames:v", "5",
             "-c:v", "libx264", "-preset", "fast", "-crf", "28",
             "-pix_fmt", "yuv420p",
             tmp_out],
            capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0,
                         f"FFmpeg mux failed:\n{result.stderr[-1000:]}")
        self.assertTrue(os.path.isfile(tmp_out), "Output MP4 not created")
        # Clean up
        try:
            os.remove(tmp_out)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
class TestBlenderSysInfo(unittest.TestCase):
    """Task 2 — GPU and render engine info from blender_sysinfo.json."""

    @classmethod
    def setUpClass(cls):
        sysinfo_path = os.path.join(OUTPUT, "blender_sysinfo.json")
        cls.sysinfo = None
        if os.path.isfile(sysinfo_path):
            with open(sysinfo_path) as f:
                cls.sysinfo = json.load(f)

    def test_sysinfo_exists(self):
        self.assertIsNotNone(self.sysinfo, "blender_sysinfo.json not found in output/")

    def test_blender_version_in_sysinfo(self):
        self.assertIn("blender_version", self.sysinfo)
        self.assertIn("4.4", self.sysinfo["blender_version"])

    def test_cycles_device_info(self):
        cycles = self.sysinfo.get("cycles_gpu", {})
        self.assertIn("devices", cycles)
        print(f"  Cycles devices: {cycles.get('devices')}")
        print(f"  Default compute type: {cycles.get('default_compute_device_type')}")

    def test_no_cuda_on_intel(self):
        cycles = self.sysinfo.get("cycles_gpu", {})
        devices = cycles.get("devices", [])
        cuda_devs = [d for d in devices if d.get("type") == "CUDA"]
        self.assertEqual(len(cuda_devs), 0,
                         f"Unexpected CUDA device found: {cuda_devs}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Blender  : {BLENDER}")
    print(f"FFmpeg   : {FFMPEG_PATH}")
    print(f"Output   : {OUTPUT}")
    print()
    unittest.main(verbosity=2)
