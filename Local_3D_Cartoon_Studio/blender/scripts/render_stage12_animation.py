"""Render opt-in animation studies with the approved Stage 10 and 11 assets."""

import argparse
import json
from math import acos, atan2, cos, floor, hypot, isfinite, pi, sin, sqrt, tau
from pathlib import Path
from random import Random
import subprocess
import sys
from time import perf_counter

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stage11_garden import PROJECT, load_cast
from facial_preview import FRONT_Y
from garden_utils import set_camera
from studio.dialogue.mouth_shapes import MouthShapes


FPS = 12
GROUND = .027
SOLO = ("idle", "walking", "waving", "pointing", "nodding", "happy", "surprised",
        "talking", "dancing", "head_shake")
PAIR = ("greeting", "smiling", "eye_contact", "camera_wave", "dance", "walking")
# Mouth half width, half height, corner lift, brow lift, brow tilt, eye openness.
FACE = {
    "neutral": (.051, .005, .006, .000, .00, 1.00),
    "happy": (.070, .017, .023, .006, .09, .90),
    "big_smile": (.082, .025, .026, .008, .13, .86),
    "sad": (.050, .006, -.016, .001, -.28, .82),
    "surprised": (.036, .038, .000, .027, .03, 1.12),
    "angry": (.049, .008, -.011, -.010, .31, .77),
    "curious": (.043, .009, .007, .007, -.15, 1.04),
    "confused": (.049, .008, -.006, .009, .22, .93),
    "excited": (.076, .029, .022, .019, .10, 1.07),
    "talking": (.052, .012, .007, .004, .05, 1.00),
}
MOUTHS = {
    "REST": FACE["neutral"][:3], "MBP": (.033, .003, .000),
    "FV": (.043, .007, .002), "TD": (.048, .012, .002),
    "WQ": (.027, .022, .000), "OPEN": (.049, .031, .001),
    "EI": (.072, .012, .014),
}


def smooth(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)


def envelope(t, start, end, fade=.35):
    return smooth((t - start) / fade) * smooth((end - t) / fade)


def blink_schedule(seed, seconds):
    rng = Random(seed)
    time = rng.uniform(.63, 1.12)
    times = []
    while time < seconds:
        times.append(round(time * FPS) / FPS)
        if rng.random() < .35:
            times.append(round((time + .23) * FPS) / FPS)
        time += rng.uniform(1.6, 3.9)
    return times


def blend_expression(expression, weight):
    return tuple(a + (b - a) * weight for a, b in zip(FACE["neutral"], FACE[expression]))


def head_features(rest, name):
    return [obj for obj in rest if obj.name.removeprefix(name + "_").startswith(
        ("Head", "Hair", "Hijab", "Eye", "Iris", "Nose", "Mouth"))]


class Performer:
    def __init__(self, cast):
        self.name, self.root, self.rest, self.meshes = cast
        self.front = FRONT_Y[self.name]
        self.heading = 0 if self.front > 0 else pi
        self.parts = {obj.name.removeprefix(self.name + "_"): obj for obj in self.rest}
        self.meshes["head"] = head_features(self.rest, self.name)
        self.meshes["chest"] = [self.parts["Torso"]]
        self.bones = self.root.pose.bones
        self.actions = {}
        assert all(bone in self.bones for bone in self.meshes)
        assert all(obj.parent == self.root for obj in self.rest)
        if self.root.animation_data:
            self.root.animation_data_clear()
        for action in ("idle", "walk", "wave", "point", "nod", "greeting"):
            source = bpy.data.actions[f"{self.name.upper()}_{action.upper()}"]
            start, end = source.frame_range
            assert start < end and source.fcurves
            curves = []
            for curve in source.fcurves:
                bone = curve.data_path.split('"')[1]
                assert bone in self.bones and curve.data_path.endswith(".rotation_euler")
                assert all(isfinite(v) for k in curve.keyframe_points for v in k.co)
                curves.append((self.bones[bone], curve))
            self.actions[action] = (start, end, curves)
        self.head = self.parts["Head"]
        self.head_rest = self.rest[self.head]
        self.mouth = self.parts["Mouth"]
        self.mouth_rest = self.rest[self.mouth]
        mesh = bpy.data.meshes.new(f"{self.name} Stage 12 mouth")
        self.mouth.data = mesh
        material = bpy.data.materials.new("Mouth interior")
        material.diffuse_color = (.075, .012, .018, 1)
        segments = 32
        triangles = [(0, n + 1, (n + 1) % segments + 1) for n in range(segments)]
        mesh.from_pydata([(0, 0, 0)] * (segments + 1), [], triangles)
        mesh.materials.append(material)
        self.closed_eye = material
        self.mouth_samples = [(0, 0)] + [(cos(n * tau / segments), sin(n * tau / segments))
                                         for n in range(segments)]
        # Include the Stage 10 sole detail in the plant height.
        self.sole = {}
        for side in "LR":
            foot = self.parts[f"Foot_{side}"]
            points = [foot.matrix_world @ Vector(p) for p in foot.bound_box]
            for detail in foot.children:
                points.extend(detail.matrix_world @ Vector(p) for p in detail.bound_box)
            inverse = self.root.matrix_world.inverted()
            self.sole[side] = min((inverse @ p).z for p in points)
        self.eye_colors = {}
        for side in "LR":
            eye = self.parts[f"Eye_{side}"]
            self.eye_colors[side] = eye.data.materials[0]
        self.previous_plants = {}
        self.max_plant_drift = 0
        self.max_plant_error = 0
        self.max_scarf_error = 0

    def action(self, name, progress, weight):
        start, end, curves = self.actions[name]
        for bone, curve in curves:
            bone.rotation_euler[curve.array_index] += curve.evaluate(start + (end - start) * progress) * weight

    def solve_leg(self, side, displacement, lift):
        """Solve two rigid leg links in the sagittal plane and keep the shoe level."""
        thigh, shin, foot = (self.bones[f"{part}_{side}"] for part in ("thigh", "shin", "foot"))
        hip = thigh.bone.head_local
        ankle = foot.bone.head_local
        d = displacement
        z = ankle.z + lift - hip.z
        a, b = thigh.bone.length, shin.bone.length
        distance = hypot(d, z)
        knee_angle = acos(min(1, (a*a + distance*distance - b*b) / (2*a*distance)))
        aim = atan2(d, -z) + self.front * knee_angle
        knee = hip + Vector((0, a*sin(aim), -a*cos(aim)))
        target = ankle + Vector((0, d, lift))
        # Set absolute rotations in armature space. The rest link directions
        # are vertical, so a rotation about X preserves the rig's bone roll.
        thigh_angle = atan2(knee.y - hip.y, hip.z - knee.z)
        shin_angle = atan2(target.y - knee.y, knee.z - target.z)
        for bone, delta in ((thigh, thigh_angle), (shin, shin_angle-thigh_angle),
                            (foot, -shin_angle)):
            rest_rotation = bone.bone.matrix_local.to_3x3()
            rotation = rest_rotation.inverted() @ Matrix.Rotation(delta, 3, "X") @ rest_rotation
            bone.rotation_euler = rotation.to_euler()
        return target

    def body(self, t, mode, duration, x, gaze, phase=0):
        for bone in self.bones:
            bone.rotation_mode = "XYZ"
            bone.rotation_euler.zero()
        aanya = self.name == "Aanya"
        rhythm = t * tau / (3.0 if aanya else 2.6)
        chest = self.bones["chest"]
        chest.rotation_euler.x = .025 * sin(rhythm)
        chest.rotation_euler.y = .028 * sin(rhythm + .3)
        head = self.bones["head"]
        head.rotation_euler.x = .034 * sin(rhythm - .4) + self.front * .18 * gaze[1]
        head.rotation_euler.y = -.48 * gaze[0] + .023 * sin(rhythm - .55)
        for side in "LR":
            self.bones[f"hand_{side}"].rotation_euler.y = .045 * sin(rhythm + (side == "R"))
        self.root.rotation_euler.z = self.heading
        self.root.location = (x, .04, GROUND - min(self.sole.values()))
        plants = []
        if mode == "walking":
            # Constant root travel while each stance ankle moves back at the
            # same speed. Swing joins adjacent stance locations with zero
            # world velocity at both endpoints.
            cycle = 1.15 if not aanya else 1.26
            speed = .27
            self.root.location.y = -.43 + speed * t
            self.root.location.z -= .024
            for side, offset in (("L", 0), ("R", .5)):
                step = (t / cycle + offset) % 1
                stance = .58
                stride = speed * cycle
                swing = (step - stance) / (1 - stance)
                disp = stride * (stance / 2 - step + smooth(swing))
                lift = .091 * sin(pi * max(0, swing)) ** 2 if step > stance else 0
                target = self.solve_leg(side, self.front * disp, lift + .024)
                if step <= stance:
                    plants.append((side, target))
                self.bones[f"upper_arm_{side}"].rotation_euler.x = self.front * .27 * cos(tau * step)
            chest.rotation_euler.x += self.front * .045
            chest.rotation_euler.y += .05 * sin(tau * t / cycle)
        elif mode in ("waving", "pointing", "greeting", "camera_wave"):
            start = phase
            weight = envelope(t, start, min(duration, start + 1.68), .34)
            u = t - start
            side = "L" if aanya else "R"
            outward = 1 if side == "L" else -1
            arm = self.bones[f"upper_arm_{side}"]
            forearm = self.bones[f"forearm_{side}"]
            wrist = self.bones[f"hand_{side}"]
            if mode == "pointing":
                arm.rotation_euler.x = self.front * .82 * weight
                arm.rotation_euler.z = -outward * .67 * weight
                forearm.rotation_euler.x = self.front * .26 * weight
                wrist.rotation_euler.y += .20 * weight
            else:
                arm.rotation_euler.z = -outward * 1.16 * weight
                arm.rotation_euler.x = self.front * .30 * weight
                forearm.rotation_euler.z = -outward * (1.00 + .21 * sin(tau * 2.35 * u)) * weight
                wrist.rotation_euler.z = -outward * .28 * sin(tau * 2.35 * u - .55) * weight
            chest.rotation_euler.y += outward * .10 * weight
            head.rotation_euler.z += outward * .08 * weight
        elif mode == "nodding":
            self.action("nod", smooth((t-.2)/(duration-.45)), .65 * self.front)
        elif mode == "head_shake":
            head.rotation_euler.y += .33 * sin(tau * 1.8 * t) * envelope(t, 0, duration)
        elif mode in ("dance", "dancing"):
            beat = tau * 1.15 * t
            strength = envelope(t, 0, duration)
            chest.rotation_euler.y += strength * .18 * sin(beat)
            head.rotation_euler.z += strength * .12 * sin(beat-.44)
            for side, offset in (("L", 0), ("R", pi)):
                outward = 1 if side == "L" else -1
                step = max(0, sin(beat + offset))
                self.bones[f"upper_arm_{side}"].rotation_euler.z = -outward * strength * (.45 + .60*step)
                self.bones[f"forearm_{side}"].rotation_euler.x = self.front * strength * (.45 + .35*step)
                self.solve_leg(side, .04 * step * strength, .035 * step * strength + .024)
            self.root.location.z -= .024
        bpy.context.view_layer.update()
        for name, objects in self.meshes.items():
            bone = self.bones[name]
            delta = bone.matrix @ bone.bone.matrix_local.inverted()
            for obj in objects:
                obj.matrix_basis = delta @ self.rest[obj]
        current_plants = {}
        for side, target in plants:
            error = (self.bones[f"foot_{side}"].head - target).length
            self.max_plant_error = max(self.max_plant_error, error)
            assert error < .001, (self.name, side, error)
            ankle = self.root.matrix_world @ self.bones[f"foot_{side}"].head
            current_plants[side] = ankle
            assert abs(ankle.z + self.sole[side] - self.bones[f"foot_{side}"].bone.head_local.z - GROUND) < .002
            if side in self.previous_plants:
                drift = (ankle - self.previous_plants[side]).length
                self.max_plant_drift = max(self.max_plant_drift, drift)
                assert drift < .002, (self.name, side, drift)
        self.previous_plants = current_plants
        if aanya:
            scarf = self.parts["Hijab_Cap"]
            relative = self.head.matrix_basis.inverted() @ scarf.matrix_basis
            expected = self.head_rest.inverted() @ self.rest[scarf]
            error = max(abs(relative[i][j]-expected[i][j]) for i in range(4) for j in range(4))
            self.max_scarf_error = max(self.max_scarf_error, error)
            assert error < .001

    def face(self, expression, weight, gaze, blink, viseme=None):
        width, height, lift, brow, tilt, eye_open = blend_expression(expression, weight)
        if viseme is not None:
            width, height, lift = MOUTHS[viseme]
        delta = self.head.matrix_basis @ self.head_rest.inverted()
        for side in "LR":
            eye = self.parts[f"Eye_{side}"]
            iris = self.parts[f"Iris_{side}"]
            eyebrow = self.parts[f"Eyebrow_{side}"]
            outward = 1 if side == "L" else -1
            openness = max(.065, (1 - blink) * eye_open)
            local = self.rest[eye].copy()
            local[2][2] *= openness
            eye.matrix_basis = delta @ local
            eye.data.materials[0] = self.closed_eye if openness < .25 else self.eye_colors[side]
            local = self.rest[iris].copy()
            # Roll off the spherical sclera as the pupil moves off axis.
            dx, dz = self.front * .019 * gaze[0], .016 * gaze[1]
            local.translation += Vector((dx, -.004*self.front*(gaze[0]**2+gaze[1]**2), dz*openness))
            local[2][2] *= openness
            iris.matrix_basis = delta @ local
            for obj in [iris, *iris.children]:
                obj.hide_render = openness < .30
            local = self.rest[eyebrow].copy()
            pos = local.translation
            asymmetry = .012 * outward * weight if expression in ("curious", "confused") else 0
            pos += Vector((0, 0, brow + asymmetry))
            local = Matrix.Translation(pos) @ Matrix.Rotation(outward * tilt, 4, "Y") @ local.to_3x3().to_4x4()
            eyebrow.matrix_basis = delta @ local

        # Project in native head space before the head rotates. The existing
        # mouth object retains its attachment; only the overlay vertices move.
        head_inverse = self.head_rest.inverted()
        mouth_inverse = self.mouth_rest.inverted()
        front = Vector((0, self.front, 0))
        ray = head_inverse.to_3x3() @ -front
        for vertex, (x, z) in zip(self.mouth.data.vertices, self.mouth_samples):
            point = self.mouth_rest.translation + Vector((width*x, 0, height*z + lift*x*x))
            if viseme == "OPEN":
                point.z -= .011
            hit, surface, _, _ = self.head.ray_cast(head_inverse @ (point + front), ray)
            assert hit, (self.name, expression, viseme, point)
            vertex.co = mouth_inverse @ (self.head_rest @ surface + .007 * front)
        self.mouth.data.update()


def speech_lines(folder):
    if folder is None:
        return {}
    package = json.loads((folder / "timing.json").read_text(encoding="utf-8"))
    lines = {}
    for scene in package["scenes"]:
        for line in scene["lines"]:
            name = line["character"]
            if name not in ("Aarav", "Aanya") or name in lines or not line.get("lipsync"):
                continue
            data = json.loads((folder / line["lipsync"]).read_text(encoding="utf-8"))
            fps, count = data["fps"], data["total_frames"]
            if data["character"] != name or fps <= 0 or count <= 0:
                raise ValueError(f"Invalid speech timing for {name}")
            visemes = {int(i): value for i, value in data["frames"].items()}
            if any(not 1 <= frame <= count or not MouthShapes.is_valid(value)
                   for frame, value in visemes.items()):
                raise ValueError(f"Invalid viseme frame for {name}")
            lines[name] = fps, count, visemes, folder / line["audio"]
    return lines


def expression_cue(mode, t, duration, index):
    if mode == "expression_study":
        name = tuple(FACE)[min(len(FACE)-1, floor(t))]
        return name, envelope(t % 1, 0, 1, .22)
    name = {
        "walking": "happy", "waving": "big_smile", "pointing": "curious",
        "nodding": "happy", "smiling": "big_smile", "greeting": "happy",
        "camera_wave": "big_smile", "eye_contact": "curious",
        "dance": "excited", "dancing": "excited",
    }.get(mode, mode if mode in FACE else "neutral")
    delay = .34 if mode == "greeting" and index == 1 else .08
    return name, envelope(t, delay, duration, .42)


def gaze_cue(mode, t, duration, index):
    if mode in ("eye_contact", "greeting", "smiling"):
        return ((-1 if index else 1) * envelope(t, .08, duration, .5), 0)
    if mode == "pointing":
        return (-.85 * envelope(t, .08, duration, .36), .22 * envelope(t, .08, duration, .36))
    if mode == "surprised":
        return (0, .6 * envelope(t, .1, duration, .3))
    if mode == "expression_study":
        return (.8*sin(pi*t/2), .65*sin(pi*t))
    return (.14 * sin(2*t+index), .10 * sin(1.5*t))


def export_clip(settings, frames, destination, count, audio):
    encode = [settings["ffmpeg_executable"], "-nostdin", "-v", "error", "-n",
              "-framerate", str(FPS), "-i", str(frames / "%04d.png")]
    if audio:
        encode.extend(["-i", str(audio), "-af", "adelay=250:all=1,apad", "-c:a", "aac"])
    encode.extend(["-frames:v", str(count), "-t", str(count / FPS), "-c:v", "libx264",
                   "-preset", "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                   str(destination)])
    subprocess.run(encode, check=True)
    subprocess.run([settings["ffmpeg_executable"], "-nostdin", "-v", "error", "-xerror",
                    "-i", str(destination), "-f", "null", "-"], check=True)
    probe = subprocess.check_output([settings["ffprobe_executable"], "-v", "error",
                                     "-show_streams", "-of", "json", str(destination)])
    streams = json.loads(probe)["streams"]
    video = next(stream for stream in streams if stream["codec_type"] == "video")
    assert (video["width"], video["height"], video["r_frame_rate"], int(video["nb_frames"])) == (640, 360, "12/1", count)
    assert any(s["codec_type"] == "audio" for s in streams) == bool(audio)


def render_study(scene, camera, cast, out, label, mode, settings, seed, speech, performers, original_visibility):
    frames = out / "frames" / label
    frames.mkdir(parents=True)
    close = mode in ("happy", "surprised", "talking", "expression_study", "eye_contact", "smiling")
    paired = len(cast) == 2
    for performer in performers:
        for obj in performer.root.children_recursive:
            obj.hide_render = original_visibility[obj] or performer not in cast
    distance = (4.25 if paired else 2.85) if close else (5.15 if paired else 4.85)
    height = 1.38 if close else .90
    set_camera(camera, (.16, distance, height+.22), (0, 0, height))
    camera.data.lens = 47 if close else 40
    scene.camera = camera
    dialogue = speech.get(cast[0].name) if mode == "talking" else None
    audio = dialogue[3] if dialogue else None
    duration = (len(FACE) if mode == "expression_study" else
                max(2.5, dialogue[1]/dialogue[0]+.6) if dialogue else
                3 if paired or mode in ("walking", "dancing", "idle") else 2)
    count = round(duration*FPS)
    schedules = [blink_schedule(seed + (0 if p.name=="Aarav" else 1), duration) for p in cast]
    evaluation = render_seconds = 0
    for p in cast:
        p.previous_plants.clear()
    for n in range(count):
        start = perf_counter()
        t = n/FPS
        scene.frame_set(n+1)
        for index, (p, blinks) in enumerate(zip(cast, schedules)):
            gaze = gaze_cue(mode, t, duration, index)
            expression, weight = expression_cue(mode, t, duration, index)
            p.body(t, mode, duration, (-.54 if index == 0 else .54) if paired else 0,
                   gaze, phase=.95*index if mode=="greeting" else .16)
            viseme = None
            if mode == "talking":
                if dialogue:
                    fps, total, keys, _ = dialogue
                    sample = 1 + floor((t-.25)*fps+1e-7)
                    viseme = keys.get(sample, "REST") if 1 <= sample <= total else "REST"
                else:
                    manual = ("REST", "MBP", "OPEN", "TD", "EI", "WQ", "FV", "REST")
                    viseme = manual[min(len(manual)-1, int(t*4))]
            blink = max((smooth(1 - abs(t - stamp)/.14) for stamp in blinks), default=0)
            p.face(expression, weight, gaze, blink, viseme)
        bpy.context.view_layer.update()
        for p in cast:
            for part in (("Head",) if close else ("Head", "Torso", "Foot_L", "Foot_R")):
                obj = p.parts[part]
                for corner in obj.bound_box:
                    x, y, z = world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner))
                    assert 0 < x < 1 and 0 < y < 1 and z > 0, (label, n, part, x, y)
        evaluation += perf_counter() - start
        scene.render.filepath = str(frames / f"{n+1:04d}.png")
        start = perf_counter()
        bpy.ops.render.render(write_still=True)
        render_seconds += perf_counter() - start
    export_clip(settings, frames, out / f"{label}.mp4", count, audio)
    return {"frames": count, "duration": count/FPS, "audio": bool(audio),
            "evaluation_seconds": round(evaluation, 3), "render_seconds": round(render_seconds, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="fresh directory for clips and PNG sequences")
    parser.add_argument("--speech-package", type=Path)
    parser.add_argument("--seed", type=int, default=1205)
    parser.add_argument("--only", nargs="+", help="render selected clip names")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    output = args.output.resolve()
    settings = json.loads((PROJECT / "config/settings.json").read_text(encoding="utf-8"))
    speech = speech_lines(args.speech_package)
    start = perf_counter()
    garden = PROJECT / "output/stage11_garden_previews/final/garden_stage11.blend"
    bpy.ops.wm.open_mainfile(filepath=str(garden))
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 6
    assert scene.render.engine == "BLENDER_WORKBENCH"
    performers = [Performer(item) for item in load_cast(scene)]
    original_visibility = {obj: obj.hide_render for p in performers for obj in p.root.children_recursive}
    camera = bpy.data.objects["Cast Medium Camera"]
    studies = {f"{p.name.lower()}_{mode}": ([p], mode)
               for p in performers for mode in (*SOLO, "expression_study")}
    studies.update({f"both_{mode}": (performers, mode) for mode in PAIR})
    if args.only and (unknown := set(args.only) - studies.keys()):
        parser.error(f"unknown clips: {sorted(unknown)}")
    output.mkdir(parents=True, exist_ok=False)
    measurements = {"resolution": [640, 360], "fps": FPS, "engine": scene.render.engine,
                    "load_seconds": round(perf_counter()-start, 3), "seed": args.seed,
                    "source_actions": {p.name: len(p.actions) for p in performers},
                    "clips": {}}
    for label, (cast, mode) in studies.items():
        if args.only and label not in args.only:
            continue
        measurements["clips"][label] = render_study(
            scene, camera, cast, output, label, mode, settings, args.seed, speech, performers, original_visibility)
    measurements["max_stance_drift_m_per_frame"] = max(p.max_plant_drift for p in performers)
    measurements["max_ankle_target_error_m"] = max(p.max_plant_error for p in performers)
    measurements["max_scarf_relative_transform_error"] = max(p.max_scarf_error for p in performers)
    (output / "measurements.json").write_text(json.dumps(measurements, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
