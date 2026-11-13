from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import bpy

spec=importlib.util.spec_from_file_location("stage10",os.environ["STAGE10_SCRIPT"])
stage=importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
out=Path(os.environ["STAGE10_REVIEW"])
stage.OUT=out/"motion_frames"
stage.OUT.mkdir(exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
stage.configure_workbench(scene)
scene.render.fps=12
scene.render.resolution_percentage=100
scene.display.shading.show_object_outline=False
scene.display.shading.show_shadows=False
scene.world.color=(.22,.31,.36)
from character_movement import _BONE_TO_MESH,_SAFE_BONES
from render_stage44_preview import dance
from mathutils import Vector
from math import pi
rigs=[]
for name,x in (("Aarav",-.74),("Aanya",.74)):
    with bpy.data.libraries.load(str(out/f"{name.lower()}_stage10.blend")) as (source,target):
        target.objects=[item for item in source.objects if item.startswith(name+"_")]
        target.actions=[item for item in source.actions if item.startswith(name.upper()+"_")]
    for obj in target.objects:
        scene.collection.objects.link(obj)
    root=stage.part(name,"Armature")
    rest={obj:obj.matrix_basis.copy() for obj in root.children}
    meshes={bone:[obj for obj in rest if obj.name.split("_",1)[1] in suffixes]
            for bone,suffixes in _BONE_TO_MESH.items() if bone in _SAFE_BONES}
    dance(name,25,36,0 if name=="Aarav" else pi)
    rigs.append((name,x,root,rest,meshes))
stage.camera(scene,(0,0,.91),(-2.6,4.8,.15),4.35)
for frame in range(1,37):
    scene.frame_set(frame)
    with ExitStack() as stack:
        for name,x,root,rest,meshes in rigs:
            root.location=(0,0,0)
            root.rotation_euler.z=0
            if frame <=24:
                kind="walk" if frame<=12 else "wave"
                for obj,matrix in rest.items():
                    obj.matrix_basis=matrix
                action=bpy.data.actions[f"{name.upper()}_{kind.upper()}"]
                stage.pose_action(root,rest,meshes,action,1+2*((frame-1)%12),24,kind)
            stack.enter_context(stage.mouth_surface(name,"happy"))
            root.location=(x,0,0)
            root.rotation_euler.z=0 if name=="Aarav" else pi
            bpy.context.view_layer.update()
            feet=[stage.part(name,f"Foot_{side}") for side in ("L","R")]
            ground=min((foot.matrix_world@Vector(corner)).z for foot in feet for corner in foot.bound_box)
            root.location.z=-ground
        stage.render(scene,f"frame_{frame:03}")
