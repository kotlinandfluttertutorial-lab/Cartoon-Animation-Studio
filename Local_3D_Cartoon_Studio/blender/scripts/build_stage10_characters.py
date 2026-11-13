"""Build and preview isolated Stage 10 character variants with the existing rigid rigs."""
from contextlib import ExitStack
import json
from math import cos, pi, sin, tau
from pathlib import Path
import sys
from time import perf_counter

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from facial_preview import FRONT_Y, mouth_surface, prepare_character_face, viseme_pose
from garden_art_direction import color, paint, rounded_mesh
from garden_utils import configure_workbench
from render_story_scene import pose_action
from studio.dialogue.expression_library import apply_expression, restore_expression

PROJECT = SCRIPTS.parents[1]
ASSETS = PROJECT / "blender/assets"
OUT = PROJECT / "output/stage10_character_previews"
PARTS = ("Head", "Torso", "Neck", "Mouth", "Eye_L", "Eye_R", "Iris_L", "Iris_R",
         "Eyebrow_L", "Eyebrow_R", "Nose", "Hand_L", "Hand_R", "Foot_L", "Foot_R")


def part(name, suffix):
    return bpy.data.objects[f"{name}_{suffix}"]


def replace_surface(obj, rings, segments=32):
    vertices = [vertex for ring in rings for vertex in ring]
    faces = []
    for row in range(len(rings) - 1):
        for i in range(segments):
            a = row * segments + i
            b = row * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    faces.extend((tuple(reversed(range(segments))), tuple(range(len(vertices)-segments, len(vertices)))))
    mesh = bpy.data.meshes.new(obj.name + "_Stage10")
    mesh.from_pydata(vertices, [], faces)
    import bmesh
    edit = bmesh.new()
    edit.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(edit, faces=list(edit.faces))
    edit.to_mesh(mesh)
    edit.free()
    for material in obj.data.materials:
        mesh.materials.append(material)
    obj.data = mesh
    for polygon in mesh.polygons:
        polygon.use_smooth = True


def profile(obj, levels):
    replace_surface(obj, [
        [(x * cos(i*tau/32), y * sin(i*tau/32), z) for i in range(32)]
        for z, x, y in levels
    ])


def detail(obj, label, pos, size, material):
    return rounded_mesh(f"{obj.name}_{label}", pos, size, material, parent=obj)


def scarf(name):
    cap = part(name, "Hijab_Cap")
    # Nested elliptical rings run from the face opening over the crown to
    # the back. The lower half widens into a shoulder-length drape.
    contours = [
        (-.255, .183, .206, 1.424), (-.251, .206, .239, 1.419),
        (-.221, .241, .269, 1.407), (-.155, .279, .288, 1.391),
        (-.055, .303, .298, 1.378), (.065, .299, .296, 1.377),
        (.173, .260, .272, 1.381), (.245, .175, .207, 1.392),
        (.279, .071, .104, 1.415), (.284, .012, .014, 1.43),
    ]
    rings = []
    for row, (depth, width, height, center) in enumerate(contours):
        ring = []
        for i in range(32):
            a = i*tau/32
            fold = max(0, -sin(a)) * min(row/4, 1) * .014 * cos(5*a)
            # Localize to the existing cap origin and scale.
            drape = max(0, -sin(a)) ** 3 * sin(pi * row / (len(contours) - 1))
            world = (width*cos(a), depth+fold, center+height*sin(a)-.155*drape)
            ring.append(tuple((world[k]-cap.location[k])/cap.scale[k] for k in range(3)))
        rings.append(ring)
    replace_surface(cap, rings)
    # The first ring is an open face aperture, the last ring closes the back.
    import bmesh
    edit = bmesh.new()
    edit.from_mesh(cap.data)
    bmesh.ops.delete(edit, geom=[f for f in edit.faces if all(v.index < 32 for v in f.verts)], context="FACES_ONLY")
    edit.to_mesh(cap.data)
    edit.free()
    lining = cap.modifiers.new("Scarf hem thickness", "SOLIDIFY")
    lining.thickness = .035
    paint(cap, color("Stage10_Scarf", "#713F92"))
    for suffix in ("Hijab_Side_L", "Hijab_Side_R", "Hijab_Back"):
        panel = part(name, suffix)
        panel.hide_render = True
        panel.hide_viewport = True


def redesign(name, root):
    prepare_character_face(name)
    front = FRONT_Y[name]
    aarav = name == "Aarav"
    fabric = color(name+"_fabric10", "#187A92" if aarav else "#B95084")
    trim = color(name+"_trim10", "#F2B949" if aarav else "#FFBB9E")
    shoes = color(name+"_shoes10", "#C86E37" if aarav else "#76365C")
    sole = color("Stage10_sole", "#F0DEC4")
    iris = color(name+"_iris10", "#50332A" if aarav else "#4A303B")
    pupil = color("Stage10_pupil", "#201723")
    white = color("Stage10_glint", "#FFFFFF")
    brow = color(name+"_brow10", "#4C2B25" if aarav else "#49303E")

    head = part(name, "Head")
    profile(head, [(-.99,.13,.17),(-.89,.42,.47),(-.73,.68,.69),(-.46,.88,.88),
                   (-.15,1,1),(.17,1.025,.99),(.45,.94,.91),(.7,.74,.74),(.89,.44,.46),(.98,.12,.15)])
    if not aarav:
        # Keep the scalp and ears inside the fitted scarf shell.
        for vertex in head.data.vertices:
            vertex.co.x *= .91
            vertex.co.z *= .92
    torso = part(name, "Torso")
    profile(torso, [(-1,.70,.78),(-.92,.86,.94),(-.64,.91,1),(.19,1.03,1),
                    (.69,1.14,.91),(.87,.92,.79),(.98,.68,.68),(1,.42,.52)])
    paint(torso, fabric)
    detail(torso,"Collar", (0,.05*front,.91),(.52,.68,.14),trim)
    for i in range(3):
        detail(torso,f"Button_{i}",(0,front*.99,.42-i*.31),(.068,.12,.073),trim)
    if not aarav:
        skirt = part(name,"Skirt")
        profile(skirt,[(-1,.98,.92),(-.88,1.02,1),(-.50,.95,.97),(.38,.82,.88),(1,.71,.81)])
        paint(skirt,fabric)
        detail(skirt,"Hem",(0,0,-.78),(.95,.96,.20),trim)
        scarf(name)
    else:
        hair = part(name,"Hair_Top")
        for modifier in list(hair.modifiers):
            hair.modifiers.remove(modifier)
        profile(hair,[(-1,.65,.77),(-.8,1.02,1.08),(-.24,1.12,1.1),(.45,1.06,1),
                      (.89,.81,.79),(1.16,.34,.40)])
        hair_mat = color("Stage10_Aarav_hair","#503228")
        paint(hair,hair_mat)
        for i in range(3):
            lock = detail(hair,f"SweptLock_{i}",(-.5+i*.43,.62,.05+i*.2),(.52,.62,.62),hair_mat)
            lock.rotation_euler.y = -.46
        for suffix in ("Hair_Front","Hair_Back"):
            obj = part(name,suffix)
            obj.hide_render = True
            obj.hide_viewport = True

    for side, sign in (("L",1),("R",-1)):
        eye = part(name,f"Eye_{side}")
        eye.location.z += .012
        eye.scale.x *= 1.14
        eye.scale.z *= 1.10
        ring = part(name,f"Iris_{side}")
        ring.location.z = eye.location.z
        ring.location.y = eye.location.y + front * .030
        paint(ring,iris)
        detail(ring,"Pupil",(0,front*.86,0),(.62,.28,.65),pupil)
        detail(ring,"Glint",(-.28,front*1.1,.28),(.22,.16,.22),white)
        eyebrow = part(name,f"Eyebrow_{side}")
        profile(eyebrow,[(-.78,.72,.8),(-.45,1,1),(.4,1,1),(.8,.75,.8)])
        eyebrow.rotation_euler.y = sign*.13
        paint(eyebrow,brow)
        for suffix in ("UpperArm","LowerArm","UpperLeg","LowerLeg"):
            limb = part(name,f"{suffix}_{side}")
            profile(limb,[(-1.08,.63,.67),(-.97,.91,.92),(-.52,.97,.97),(.34,1.06,1.04),
                          (.83,1.15,1.07),(1.02,.99,.97),(1.13,.59,.62)])
            if suffix == "UpperArm":
                # Extend the shoulder cap inward in mesh space. The action pivot stays put.
                for vertex in limb.data.vertices:
                    vertex.co.x -= sign * 1.10 * max(0, vertex.co.z) ** 2
                paint(limb,fabric)
                detail(limb,"Cuff",(0,0,-.81),(.92,.95,.16),trim)
        hand = part(name,f"Hand_{side}")
        profile(hand,[(-1,.32,.48),(-.83,.66,.74),(-.30,.91,1),(.38,.91,.94),(.84,.68,.72),(1,.47,.53)])
        skin = hand.data.materials[0]
        detail(hand,"Thumb",(-sign*.71,front*.10,.03),(.39,.60,.42),(skin,skin.diffuse_color))
        foot = part(name,f"Foot_{side}")
        profile(foot,[(-1,.71,.83),(-.87,.99,1),(-.48,1,1),(.18,.96,.96),(.72,.81,.74),(1,.54,.52)])
        paint(foot,shoes)
        detail(foot,"Sole",(0,0,-.79),(.99,1.02,.19),sole)
        detail(foot,"Strap",(0,front*.13,.65),(.80,.29,.16),trim)
    nose = part(name,"Nose")
    nose.scale *= 1.10
    bpy.context.view_layer.update()


def camera(scene, target, direction, width):
    lens = bpy.data.cameras.new("Stage 10 camera")
    lens.type = "ORTHO"
    lens.ortho_scale = width
    obj = bpy.data.objects.new(lens.name,lens)
    scene.collection.objects.link(obj)
    obj.location = Vector(target)+Vector(direction)
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    scene.camera = obj


def render(scene, label):
    started = perf_counter()
    scene.render.filepath = str(OUT / (label+".png"))
    bpy.ops.render.render(write_still=True)
    return round(perf_counter()-started,3)


def preview(scene, name, root, label, view=(0,4.5,.05), emotion="neutral", viseme="REST"):
    camera(scene,(0,0,.90),(view[0],view[1]*FRONT_Y[name],view[2]),3.55)
    saved = apply_expression(name,emotion)
    try:
        with viseme_pose(part(name,"Mouth"),viseme), mouth_surface(name,emotion if viseme=="REST" else viseme):
            bpy.context.view_layer.update()
            for obj in root.children:
                if obj.type == "MESH" and not obj.hide_render:
                    x, y, depth = world_to_camera_view(scene, scene.camera, obj.matrix_world.translation)
                    assert 0 < x < 1 and 0 < y < 1 and depth > 0, (label, obj.name)
            return render(scene,name.lower()+"_"+label)
    finally:
        restore_expression(saved)


def signature(root):
    return {
        "bones": {bone.name: (bone.parent.name if bone.parent else None, tuple(tuple(row) for row in bone.matrix_local))
                  for bone in root.data.bones},
        "actions": {
            action.name: [(curve.data_path,curve.array_index,[tuple(key.co) for key in curve.keyframe_points])
                          for curve in action.fcurves]
            for action in bpy.data.actions if action.name.startswith(root.name.split("_",1)[0].upper()+"_")
        },
    }


def build_solo(name):
    started = perf_counter()
    bpy.ops.wm.open_mainfile(filepath=str(ASSETS/f"characters/{name.lower()}/{name.lower()}_stage4.blend"))
    load_seconds = perf_counter()-started
    scene = bpy.context.scene
    root = part(name,"Armature")
    original = signature(root)
    originals = {obj.name: obj.parent for obj in root.children}
    baseline_polygons = sum(len(obj.data.polygons) for obj in root.children if obj.type == "MESH")
    # Render rig mapping comes from the existing story sampler. Capture the native rest pose first.
    from character_movement import _BONE_TO_MESH, _SAFE_BONES
    for obj in [root,*root.children]:
        if obj.animation_data:
            obj.animation_data.use_nla = False
            obj.animation_data.action = None
    redesign(name,root)
    assert signature(root) == original
    assert all(part(name,suffix).type == "MESH" for suffix in PARTS)
    assert all(bpy.data.objects[n].parent == parent for n,parent in originals.items())
    assert all(len(obj.data.polygons) and all(obj.data.materials) and len(obj.data.materials)
               for obj in root.children_recursive if obj.type=="MESH")
    rest = {obj:obj.matrix_basis.copy() for obj in root.children}
    meshes = {bone:[obj for obj in rest if obj.name.split("_",1)[1] in suffixes]
              for bone,suffixes in _BONE_TO_MESH.items() if bone in _SAFE_BONES}
    meshes["head"] = [obj for obj in rest if obj.name.split("_",1)[1].startswith(
        ("Head","Hair","Hijab","Eye","Iris","Nose","Mouth"))]
    configure_workbench(scene)
    scene.render.resolution_percentage = 100
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_shadows = False
    scene.display.shading.cavity_type = "WORLD"
    scene.world.color = (.22,.31,.36)
    timings = {}
    for label,view,emotion,viseme in (
        ("idle_front",(0,4.5,.05),"neutral","REST"),
        ("idle_three_quarter",(2.4,4.5,.12),"neutral","REST"),
        ("side",(4.5,0,.05),"neutral","REST"),
        ("happy",(0,4.5,.05),"happy","REST"),
        ("surprised",(0,4.5,.05),"surprised","REST"),
        ("speaking",(0,4.5,.05),"happy","OPEN"),
    ):
        timings[label] = preview(scene,name,root,label,view,emotion,viseme)
    tested = {}
    for action_name, curves in original["actions"].items():
        action = bpy.data.actions[action_name]
        assert curves
        for path,index,_ in curves:
            if path.startswith('pose.bones['):
                assert path.split('"')[1] in root.pose.bones, path
        kind = action_name.split("_",1)[1].lower()
        start,end = action.frame_range
        sampled = []
        for frame in (1, 1+(end-start)*.22, 1+(end-start)*.45, 1+(end-start)*.72):
            pose_action(root,rest,meshes,action,frame,24,kind)
            bpy.context.view_layer.update()
            for side in ("L","R"):
                shoulder = part(name,f"UpperArm_{side}").matrix_world.translation
                assert (shoulder-part(name,"Torso").matrix_world.translation).length < .58
                foot = part(name,f"Foot_{side}").matrix_world.translation
                assert abs(foot.z) < .7
            sampled.append(tuple(round(x,5) for obj in rest for row in obj.matrix_basis for x in row))
            if kind in ("walk","wave","nod") and len(sampled)==2:
                timings[kind] = preview(scene,name,root,kind,(-4.5 if kind=="wave" else 1.1,2.5 if kind=="wave" else 4.5,.10),"happy")
        tested[action_name] = {"samples":len(sampled),"distinct_mesh_poses":len(set(sampled))}
    for obj,matrix in rest.items():
        obj.matrix_basis = matrix
    for bone in root.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    assert signature(root) == original
    root["stage10_face_ready"] = True
    for action in bpy.data.actions:
        if action.name in original["actions"]:
            action.use_fake_user = True
    scene.camera = bpy.data.objects.get("Stage 10 camera")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f"{name.lower()}_stage10.blend"))
    graph = bpy.context.evaluated_depsgraph_get()
    meshes_visible = [obj for obj in root.children_recursive if obj.type=="MESH" and not obj.hide_render]
    return {
        "load_seconds":round(load_seconds,4),"bones":len(original["bones"]),"actions":tested,
        "visible_meshes":len(meshes_visible),"source_base_polygons":baseline_polygons,
        "polygons":sum(len(obj.evaluated_get(graph).data.polygons) for obj in meshes_visible),
        "render_seconds":timings,
    }


def pair(garden):
    if garden:
        bpy.ops.wm.open_mainfile(filepath=str(ASSETS/"environments/garden/garden.blend"))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    configure_workbench(scene)
    scene.render.resolution_percentage = 100
    scene.display.shading.show_object_outline = False
    scene.display.shading.cavity_type = "WORLD"
    if not garden:
        scene.display.shading.show_shadows = False
        scene.world.color = (.22,.31,.36)
    with ExitStack() as stack:
        for name,x in (("Aarav",-.71),("Aanya",.71)):
            with bpy.data.libraries.load(str(OUT/f"{name.lower()}_stage10.blend")) as (source,target):
                target.objects = [item for item in source.objects if item.startswith(name+"_")]
            for obj in target.objects:
                scene.collection.objects.link(obj)
            root = part(name,"Armature")
            emotion = "happy" if garden else "neutral"
            apply_expression(name,emotion)
            stack.enter_context(mouth_surface(name,emotion))
            root.location = (x,-.2,.012)
            root.rotation_euler.z = 0 if name=="Aarav" else pi
        camera(scene,(0,0,1.02 if garden else .90),(.55,3.8, .65 if garden else .1),4.35 if garden else 3.85)
        if garden:
            return {"pair_garden":render(scene,"pair_garden")}
        first = render(scene,"pair_standing")
        with ExitStack() as smiles:
            for name in ("Aarav","Aanya"):
                apply_expression(name,"happy")
                smiles.enter_context(mouth_surface(name,"happy"))
            second = render(scene,"pair_smiling")
        return {"pair_standing":first,"pair_smiling":second}


if __name__ == "__main__":
    if "--" in sys.argv:
        OUT = Path(sys.argv[sys.argv.index("--")+1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT/"measurements.json").exists(), "Use a fresh output directory."
    result = {name:build_solo(name) for name in ("Aarav","Aanya")}
    result["pair_seconds"] = {**pair(False),**pair(True)}
    (OUT/"measurements.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
