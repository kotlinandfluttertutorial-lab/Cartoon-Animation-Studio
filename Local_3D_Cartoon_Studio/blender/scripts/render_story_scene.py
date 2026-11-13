"""Render requested frames of a planned garden scene in Blender Workbench."""

from contextlib import ExitStack
import json
from math import pi, tau
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_movement import _apply_pose_from_action, _BONE_TO_MESH, _SAFE_BONES
from facial_preview import mouth_surface, prepare_character_face, viseme_pose
from garden_utils import configure_workbench
from render_stage44_preview import append_character, camera_move, dance, flying_bird
from studio.dialogue.expression_library import apply_expression, restore_expression


def rig_performance(scene, performance, total):
    character = performance["character"]
    root = append_character(scene, character)
    prepare_character_face(character)
    rest = {obj: obj.matrix_basis.copy() for obj in root.children}
    meshes = {}
    for bone, suffixes in _BONE_TO_MESH.items():
        if bone in _SAFE_BONES:
            meshes[bone] = [
                obj for obj in rest if obj.name.split("_", 1)[1] in suffixes
            ]
    meshes["head"] = [
        obj for obj in rest
        if obj.name.split("_", 1)[1].startswith(
            ("Head", "Hair", "Hijab", "Eye", "Iris", "Nose", "Mouth")
        )
    ]
    action_name = performance["action"]
    if action_name == "dance":
        dance(character, 1, total, 0 if character == "Aarav" else pi)
    if action_name in ("dance", "turn"):
        return root, rest, meshes, None
    action = bpy.data.actions[f"{character.upper()}_{action_name.upper()}"]
    return root, rest, meshes, action


def pose_action(root, rest, meshes, action, frame, fps, action_name):
    start, end = action.frame_range
    elapsed = (frame - 1) * 24 / fps
    sample = start + elapsed % max(1, end - start) if action_name in ("idle", "walk") else min(end, start + elapsed)
    _apply_pose_from_action(root, action, sample)
    bpy.context.view_layer.update()
    for bone_name, objects in meshes.items():
        bone = root.pose.bones.get(bone_name)
        if bone is None:
            continue
        delta = bone.matrix @ bone.bone.matrix_local.inverted()
        for obj in objects:
            obj.matrix_basis = delta @ rest[obj]


def camera_for_scene(scene, name, total):
    width = {"wide": 6.6, "medium": 5.8, "close": 5.35, "approach": 6.5, "follow": 5.9, "pullback": 5.45}[name]
    target = (0, 0, 1.42)
    start = ((0.55, 3.9, 2.2), target, width)
    end = {
        "approach": ((0, 3.6, 2.12), target, 5.65),
        "follow": ((-0.75, 3.7, 2.15), target, width),
        "pullback": ((0.15, 4.05, 2.38), target, 6.7),
    }.get(name, start)
    scene.camera = camera_move(scene, f"Story camera {name}", 1, total, start, end)


def check_performer(scene, character, root, frame):
    camera = scene.camera
    front = camera.matrix_world.to_quaternion() @ Vector((0, 0, 1))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    foot_heights = []
    torso = bpy.data.objects[f"{character}_Torso"].matrix_world.translation
    for side in ("L", "R"):
        arm = bpy.data.objects[f"{character}_UpperArm_{side}"]
        if (arm.matrix_world.translation - torso).length > 0.5:
            raise ValueError(f"{arm.name} is detached at frame {frame}.")
    for suffix in ("Head", "Torso", "Foot_L", "Foot_R"):
        obj = bpy.data.objects[f"{character}_{suffix}"]
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        for corner in corners:
            x, y, depth = world_to_camera_view(scene, camera, corner)
            if not (0 < x < 1 and 0 < y < 1 and depth > camera.data.clip_start):
                raise ValueError(f"{obj.name} leaves the camera frame at frame {frame}.")
        center = obj.matrix_world.translation
        origin = center + front * (camera.location - center).dot(front)
        hit, _, _, _, visible, _ = scene.ray_cast(depsgraph, origin, -front)
        if not hit or visible not in root.children_recursive:
            obstruction = visible.name if hit else "no mesh hit"
            raise ValueError(f"{obj.name} is obstructed at frame {frame}: {obstruction}.")
        if suffix.startswith("Foot"):
            foot_heights.append(min(corner.z for corner in corners))
    if not 0 <= min(foot_heights) <= 0.025:
        raise ValueError(f"{character} has no grounded foot at frame {frame}.")


def render_job(job):
    scene = bpy.context.scene
    configure_workbench(scene)
    if job.get("visual_upgrade"):
        from garden_art_direction import dress_garden, soften_character

        dress_garden(scene)
    scene.render.resolution_x = job["width"]
    scene.render.resolution_y = job["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = job["fps"]
    scene.render.fps_base = 1
    scene.render.image_settings.color_mode = "RGB"
    scene.timeline_markers.clear()
    total = job["total_frames"]
    scene.frame_start, scene.frame_end = 1, total

    performance = job["scene"]["performances"]
    rigs = [rig_performance(scene, spec, total) for spec in performance]
    if job.get("visual_upgrade"):
        for root, _, _, _ in rigs:
            soften_character(root)
    camera_for_scene(scene, job["scene"]["camera"], total)
    if any(cue["effect"] == "bird_chirp" for cue in job["scene"]["sound_effects"]):
        flying_bird(scene, "Story bird", "#4BADE8", 1, total, -0.5, 2.15)
        if not performance:
            flying_bird(scene, "Garden swallow", "#B16CF0", 1, total, -0.9, 2.47)

    output = Path(job["output"])
    for frame in job["frames"]:
        # Reset animated root transforms before sampling native-space actions.
        for root, _, _, _ in rigs:
            root.location = (0, 0, 0)
            root.rotation_euler.z = 0
        scene.frame_set(frame)
        with ExitStack() as mouths:
            for spec, (root, rest, meshes, action) in zip(performance, rigs, strict=True):
                character = spec["character"]
                entrance = spec.get("entrance", False)
                walk_progress = min(1, (frame - 1) / (3 * job["fps"])) if entrance else 1
                if action is not None:
                    if entrance and walk_progress == 1:
                        idle = bpy.data.actions[f"{character.upper()}_IDLE"]
                        pose_action(root, rest, meshes, idle, frame - 3 * job["fps"], job["fps"], "idle")
                    else:
                        pose_action(root, rest, meshes, action, frame, job["fps"], spec["action"])
                # Integer frame conversion preserves the Stage 5 frame intervals.
                source_frame = (frame - 1) * job["timing_fps"] // job["fps"] + 1
                emotion, viseme = spec["expression"], "REST"
                for line in job["lines"]:
                    local_frame = source_frame - line["start_frame"] + 1
                    if line["character"] == character and 1 <= local_frame <= line["duration_frames"]:
                        emotion = line["emotion"]
                        viseme = line["shapes"].get(str(local_frame), "REST")
                        break
                mouth = bpy.data.objects[f"{character}_Mouth"]
                saved = apply_expression(character, emotion)
                # Register restoration before the temporary geometry contexts.
                mouths.callback(restore_expression, saved)
                mouths.enter_context(viseme_pose(mouth, viseme))
                mouths.enter_context(mouth_surface(character, emotion if viseme == "REST" else viseme))
                facing = 0 if character == "Aarav" else pi
                if spec["action"] == "turn":
                    facing += tau * (frame - 1) / max(1, total - 1)
                root.rotation_euler.z = facing
                travel = walk_progress * walk_progress * (3 - 2 * walk_progress)
                root.location = (-0.75 if character == "Aarav" else 0.75, -0.2 - 1.2 * (1 - travel), 0)
                bpy.context.view_layer.update()
                feet = [bpy.data.objects[f"{character}_Foot_{side}"] for side in ("L", "R")]
                sole = min((foot.matrix_world @ Vector(corner)).z for foot in feet for corner in foot.bound_box)
                root.location.z = 0.012 - sole

            bpy.context.view_layer.update()
            for spec, (root, _, _, _) in zip(performance, rigs, strict=True):
                check_performer(scene, spec["character"], root, frame)

            path = output / f"frame_{frame:04}.png"
            temporary = path.with_suffix(".partial.png")
            scene.render.filepath = str(temporary)
            bpy.ops.render.render(write_still=True)
            temporary.replace(path)
    print("STORY_SCENE_RENDER_OK")


if __name__ == "__main__":
    path = Path(sys.argv[sys.argv.index("--") + 1])
    render_job(json.loads(path.read_text(encoding="utf-8")))
