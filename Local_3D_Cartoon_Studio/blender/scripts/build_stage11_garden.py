"""Build the opt-in Stage 11 garden and render its review views in Workbench."""

import argparse
from contextlib import ExitStack
import json
from math import cos, sin, tau, pi
from pathlib import Path
from random import Random
import sys
from time import perf_counter

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from garden_utils import configure_workbench, create_material, set_camera
from facial_preview import mouth_surface
from render_stage44_preview import flying_bird
from render_story_scene import pose_action
from character_movement import _BONE_TO_MESH, _SAFE_BONES

PROJECT = SCRIPTS.parents[1]
MODELS = PROJECT / "output/stage10_character_previews/final"
RNG = Random(1103)


def material(name, hex_color):
    return create_material("Stage11 " + name, hex_color)[0]


def template(kind):
    if kind == "sphere":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2)
    elif kind == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=10)
    else:
        bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    for face in mesh.polygons:
        face.use_smooth = kind == "sphere"
    return mesh


class Garden:
    def __init__(self, scene):
        self.scene = scene
        self.templates = {kind: template(kind) for kind in ("sphere", "cylinder", "cube")}
        self.meshes = {}

    def mesh(self, name, vertices, faces, colors, groups, collection):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        for mat in colors:
            mesh.materials.append(mat)
        for polygon, index in zip(mesh.polygons, groups, strict=True):
            polygon.material_index = index
        obj = bpy.data.objects.new(name, mesh)
        bpy.data.collections[collection].objects.link(obj)
        return obj

    def piece(self, name, kind, position, scale, mat, collection):
        key = kind, mat.name
        if key not in self.meshes:
            mesh = self.templates[kind].copy()
            mesh.materials.append(mat)
            self.meshes[key] = mesh
        obj = bpy.data.objects.new(name, self.meshes[key])
        bpy.data.collections[collection].objects.link(obj)
        obj.location = position
        obj.scale = scale
        return obj

    def branch(self, name, start, end, radius, mat):
        direction = Vector(end) - Vector(start)
        obj = self.piece(name, "cylinder", (Vector(start)+Vector(end))/2,
                         (radius, radius, direction.length/2), mat, "Environment_Trees")
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def path_center(y):
    return .44 * sin(y * .64)


def terrain(g):
    grass = [material("meadow", c) for c in ("#72AA46", "#81B54E", "#8BBD58")]
    coords = [(x, y, 0 if abs(x)<3 else .045*(abs(x)-3)*sin(y*.45))
              for y in range(-12,10) for x in range(-13,14)]
    faces = [(i,i+1,i+28,i+27) for i in range(len(coords)-28) if i%27!=26]
    g.mesh("Ground_Plane", coords, faces, grass, [int(RNG.random()>.80) for _ in faces], "Environment_Ground")
    for name, half, z, color in (
        ("Path edges", 1.36, .012, "#B79B6D"), ("Path_Main", 1.27, .019, "#F2D7A1"),
    ):
        verts = [(path_center(y)+side*half, y, z) for y in (i/6 for i in range(-53,49)) for side in (-1,1)]
        faces = [(i,i+1,i+3,i+2) for i in range(0,len(verts)-2,2)]
        g.mesh(name,verts,faces,[material(name,color)],[0]*len(faces),"Environment_Path")


def plantings(g):
    bark = material("warm bark", "#885232")
    leaves = [material("canopy "+str(i), c) for i,c in enumerate(
        ("#53864B","#78A747","#A8C650","#D0C257","#D98B68","#4D9164"))]
    for index,(x,y,h,theme) in enumerate([
        (-4.8,1.7,3.9,0),(4.9,1.8,3.6,4),(-3.6,-2.5,3.2,1),(3.9,-2.8,3.6,2),
        (-5.7,-5.2,4.6,2),(5.8,-5.8,4.1,5),(-2.8,-7.3,3.2,0),(2.8,-7.7,3.9,1),
        (-7,-8.7,4.1,5),(7,-9,4.5,3),
    ]):
        top=(x+.12,y,h*.77)
        g.branch(f"Tree {index} trunk",(x,y,0),top,h*.054,bark)
        for side in (-1,1):
            g.branch(f"Tree {index} branch", (x,y,h*.42),(x+side*h*.22,y,h*.77),h*.026,bark)
        for j,(dx,dy,dz) in enumerate(((0,0,.06),(-.22,-.04,-.06),(.21,.04,-.03),(.02,.14,.09),(.12,-.10,.16))):
            g.piece(f"Tree {index} crown {j}","sphere",(x+dx*h,y+dy*h,h*(.77+dz)),
                    (h*.28,h*.25,h*.23),leaves[(theme+(j%3==0))%len(leaves)],"Environment_Trees")
    for i,(x,y) in enumerate([(-2.8,2.8),(3.6,2.8),(-3.3,-.6),(3.9,-.7),(-4,-4),(4.7,-4.9),
                              (-2.4,-5.6),(2.5,-5.8),(-5.3,.1),(5.8,0),(-2.4,-7.4),(2.3,-7.7)]):
        for j in range(3):
            size=RNG.uniform(.26,.54)
            g.piece(f"Hedge {i}.{j}","sphere",(x+(j-1)*.36,y+RNG.uniform(-.22,.22),size*.61),
                    (size*1.18,size,size),leaves[(i+j)%3],"Environment_Bushes")

    flower_colors = [material("petal "+str(i),c) for i,c in enumerate(
        ("#E96B86","#EAB344","#C18DE4","#FFF1CB","#75BBD9"))]
    center = material("pollen","#EBAB43")
    blade = material("leaf green","#4B853C")
    verts,faces,ids=[],[],[]
    def face(points, index):
        start=len(verts)
        verts.extend(points)
        faces.append(tuple(range(start,len(verts))))
        ids.append(index)
    for side in (-1,1):
        for band,y0 in enumerate((3.5,1.0,-1.6,-3.8,-5.9)):
            for _ in range(27):
                y=y0+RNG.uniform(-.68,.68)
                x=path_center(y)+side*RNG.uniform(1.67,2.6)
                h=RNG.uniform(.16,.43)
                radius=RNG.uniform(.055,.105)
                face(((x-.013,y,.025),(x+.013,y,.025),(x+.012,y,h),(x-.012,y,h)),6)
                for sign in (-1,1):
                    face(((x,y,.04),(x+sign*.094,y-.018,h*.72),(x+sign*.044,y+.026,h*.39)),6)
                for petal in range(5):
                    a=petal*tau/5
                    face(tuple(
                        (x+cos(a)*radial-sin(a)*lateral,
                         y+sin(a)*radial+cos(a)*lateral,
                         h+.032*radial/radius-.34*(sin(a)*radial+cos(a)*lateral))
                        for j in range(8)
                        for radial, lateral in [(
                            radius*(.55+.45*cos(j*tau/8)), radius*.25*sin(j*tau/8)
                        )]
                    ),band%5)
                face(tuple((x+.023*cos(i*tau/8),y+.023*sin(i*tau/8),h+.017) for i in range(8)),5)
    g.mesh("Wildflower borders",verts,faces,[*flower_colors,center,blade],ids,"Environment_Flowers")

    verts,faces,ids=[],[],[]
    for _ in range(580):
        x,y=RNG.uniform(-7,7),RNG.uniform(-8,5)
        if abs(x-path_center(y))<1.55:
            continue
        for i in range(3):
            dx=RNG.uniform(-.055,.055)
            face(((x+dx-.016,y,.018),(x+dx+.016,y,.018),
                  (x+dx+RNG.uniform(-.07,.07),y+.03,RNG.uniform(.065,.16))),i%2)
    g.mesh("Batched meadow tufts",verts,faces,[blade,leaves[2]],ids,"Environment_Flowers")


def decorations(g):
    wood=material("cedar","#BA784F")
    top=material("sunlit cedar","#DE9C65")
    stone=material("stone","#B6AF97")
    water=material("pond teal","#61B9BB")
    lily=material("lily pad","#659C51")
    cloud=material("cloud","#FFF5DF")
    hill=material("distant hills","#84BBA0")
    decor="Environment_Decorations"
    def cube(name, pos, scale, mat=wood):
        return g.piece(name,"cube",pos,scale,mat,decor)
    # Back fence leaves a clear opening for the route.
    for side in (-1,1):
        for i in range(22):
            x=side*(1.62+i*.31)
            cube(f"Fence picket {side}.{i}",(x,-6.55,.66),(.145,.069,.66),top if i%4==0 else wood)
        for z in (.32,1.0):
            cube(f"Fence rail {side} {z}",(side*4.9,-6.63,z),(3.4,.085,.063))
        for x in (1.5,4.2,6.9):
            cube(f"Fence post {side} {x}",(side*x,-6.52,.73),(.13,.15,.73),top)
    for i in range(4):
        cube(f"Bench seat slat {i}",(-3.08,-1.95+i*.13,.49),(.63,.056,.05),top)
        cube(f"Bench back slat {i}",(-3.08,-2.02,.66+i*.102),(.63,.058,.043),top)
    for dx in (-.47,.47):
        cube(f"Bench support {dx}",(-3.08+dx,-1.76,.24),(.073,.26,.24))
        cube(f"Bench back support {dx}",(-3.08+dx,-2.07,.61),(.064,.06,.56))
    for i in range(7):
        a=i*tau/7
        g.piece(f"Pond rim stone {i}","sphere",(3.6+1.03*cos(a),-1.55+.66*sin(a),.1),
                (.43,.32,.17),stone,decor)
    g.piece("Pond water","cylinder",(3.6,-1.55,.07),(1.09,.72,.065),water,decor)
    for i,(x,y) in enumerate(((3.3,-1.5),(3.83,-1.7),(3.66,-1.23))):
        g.piece(f"Lily pad {i}","cylinder",(x,y,.144),(.19,.15,.012),lily,decor)
    for i in range(4):
        g.piece(f"Bench stepping stone {i}","sphere",(-1.72-i*.25,-1.28-i*.12,.035),
                (.135,.17,.045),stone,decor)
    for i,(x,y) in enumerate(((-3.8,1.8),(3.4,2.1),(-4.05,-3.1))):
        g.piece(f"Border rock {i}","sphere",(x,y,.13),(.33,.24,.19),stone,decor)
    cube("Garden sign post",(2.65,-4.1,.46),(.075,.075,.46))
    cube("Garden sign board",(2.65,-4.1,.83),(.35,.075,.16),top)
    for i,x in enumerate((-10,-6,-2,2,6,10)):
        g.piece(f"Background hill {i}","sphere",(x,-11.7,-.15),(2.9,1.6,1.4+(i%3)*.36),hill,"Environment_Sky")
    for i,(x,z) in enumerate(((-7,4.6),(-2.5,5.15),(2.7,4.76),(7.3,5.33))):
        for j in range(4):
            g.piece(f"Cloud {i}.{j}","sphere",(x+j*.46,-11.2,z+.14*sin(j)),
                    (.64,.36,.25),cloud,"Environment_Sky")
    for i,(x,y,z) in enumerate(((-2.25,.8,.78),(2.15,-.9,.64))):
        body=material(f"butterfly {i}","#B481CF" if i else "#F2AE54")
        for side in (-1,1):
            wing=g.piece(f"Butterfly {i} wing {side}","sphere",(x+side*.068,y,z),
                         (.087,.022,.067),body,decor)
            wing.rotation_euler.y=side*.42


def camera(scene,name,position,target,lens):
    data=bpy.data.cameras.new(name)
    data.lens=lens
    obj=bpy.data.objects.new(name,data)
    bpy.data.collections["Cameras"].objects.link(obj)
    set_camera(obj,position,target)
    return obj


def load_cast(scene):
    cast=[]
    for name,x in (("Aarav",-.62),("Aanya",.62)):
        with bpy.data.libraries.load(str(MODELS/f"{name.lower()}_stage10.blend")) as (source,target):
            target.objects=[n for n in source.objects if n.startswith(name+"_")]
            target.actions=[n for n in source.actions if n.startswith(name.upper()+"_")]
        for obj in target.objects:
            scene.collection.objects.link(obj)
        root=bpy.data.objects[f"{name}_Armature"]
        rest={obj:obj.matrix_basis.copy() for obj in root.children}
        meshes={bone:[obj for obj in rest if obj.name.split("_",1)[1] in suffixes]
                for bone,suffixes in _BONE_TO_MESH.items() if bone in _SAFE_BONES}
        root.rotation_euler.z=0 if name=="Aarav" else pi
        root.location=(x,.05,.027)
        cast.append((name,root,rest,meshes))
    bpy.context.view_layer.update()
    return cast


def sightlines(scene, cast):
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    for name,root,_,_ in cast:
        for part in ("Head","Torso","Foot_L","Foot_R"):
            target=bpy.data.objects[f"{name}_{part}"].matrix_world.translation
            x,y,z=world_to_camera_view(scene,scene.camera,target)
            assert .025<x<.975 and .025<y<.975 and z>0,(scene.camera.name,name,part,x,y)
            direction=target-scene.camera.location
            hit,_,_,_,obj,_=scene.ray_cast(deps,scene.camera.location,direction.normalized(),distance=direction.length+.03)
            assert hit and obj in root.children_recursive,(scene.camera.name,name,part,obj)


def walking_lane(scene):
    deps=bpy.context.evaluated_depsgraph_get()
    count=0
    for y in (-5,-4,-3,-2,-1,0,1,2,3,4,5):
        for dx in (-.92,-.46,0,.46,.92):
            hit,point,_,_,obj,_=scene.ray_cast(deps,Vector((path_center(y)+dx,y,2)),Vector((0,0,-1)))
            assert hit and obj.name=="Path_Main" and abs(point.z-.019)<.001,(y,dx,obj)
            count+=1
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    start=perf_counter()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    for name in ("Environment_Ground","Environment_Path","Environment_Trees","Environment_Bushes",
                 "Environment_Flowers","Environment_Decorations","Environment_Sky","Lighting","Cameras"):
        scene.collection.children.link(bpy.data.collections.new(name))
    configure_workbench(scene)
    scene.view_settings.view_transform="Standard"
    scene.view_settings.exposure=.55
    scene.world.color=(.25,.55,.76)
    shading=scene.display.shading
    shading.show_object_outline=False
    shading.cavity_type="WORLD"
    shading.cavity_ridge_factor=.21
    shading.cavity_valley_factor=.55
    shading.shadow_intensity=.23
    shading.studio_light="paint.sl"
    scene.render.resolution_percentage=100
    sun=bpy.data.lights.new("Garden sunlight","SUN")
    sun.energy=1.8
    sun.angle=.23
    light=bpy.data.objects.new(sun.name,sun)
    bpy.data.collections["Lighting"].objects.link(light)
    light.rotation_euler=(.50,-.55,-.22)
    g=Garden(scene)
    terrain(g)
    plantings(g)
    decorations(g)
    for i in range(2):
        flying_bird(scene,f"Garden bird {i}","#66BAD3" if i==0 else "#E99870",1,48,-3.2-i*.8,2.55+i*.33)
    scene.frame_set(16)
    setups={
        "garden_wide":("Garden_Wide_Camera",(5.4,10.4,5.7),(0,-2.1,1.10),30),
        "garden_front":("Garden_Main_Camera",(0,8.8,2.85),(0,-2.5,1.35),31),
        "garden_three_quarter":("Garden_Close_Camera",(-5.2,7.7,3.65),(0,-2.5,1.3),32),
        "pathway_close":("Pathway Camera",(.75,5.5,1.15),(0,-2.4,.65),29),
        "trees_bushes":("Trees Camera",(-1.2,4.3,2.2),(-3.6,-1.8,1.65),46),
        "flowers_grass":("Flowers Camera",(-1.55,4.35,.83),(-2.25,2.65,.22),43),
        "bench_decor":("Bench Camera",(-1.1,1.2,1.63),(-3.03,-1.77,.58),46),
        "garden_with_characters":("Cast Medium Camera",(.4,5.6,2.02),(0,-.2,1.08),39),
        "character_walking":("Walk Camera",(1.2,5.6,1.78),(0,-.6,1.03),38),
        "final_composition":("Interaction Camera",(-1.05,4.9,1.87),(0,-.35,1.14),39),
    }
    cameras={label:camera(scene,*values) for label,values in setups.items()}
    scene.camera=cameras["garden_front"]
    bpy.context.view_layer.update()
    route_checks=walking_lane(scene)
    environment=[obj for obj in scene.objects if obj.type=="MESH"]
    assert all(obj.data and len(obj.data.polygons) and all(obj.data.materials) and len(obj.data.materials) for obj in environment)
    polygons=sum(len(obj.data.polygons) for obj in environment)
    assert polygons < 55_000,polygons
    build_seconds=perf_counter()-start
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"garden_stage11.blend"))
    load_started=perf_counter()
    bpy.ops.wm.open_mainfile(filepath=str(out/"garden_stage11.blend"))
    load_seconds=perf_counter()-load_started
    scene=bpy.context.scene
    cameras={label:bpy.data.objects[values[0]] for label,values in setups.items()}
    times={}
    def render(label):
        scene.camera=cameras[label]
        scene.render.filepath=str(out/f"{label}.png")
        started=perf_counter()
        bpy.ops.render.render(write_still=True)
        times[label]=round(perf_counter()-started,3)
    for label in list(setups)[:7]:
        render(label)

    cast=load_cast(scene)
    cast_timings={}
    with ExitStack() as stack:
        for name,root,_,_ in cast:
            orientation=root.rotation_euler.z
            root.rotation_euler.z=0
            stack.enter_context(mouth_surface(name,"happy"))
            root.rotation_euler.z=orientation
        for label in ("garden_with_characters","character_walking","final_composition"):
            if label!="garden_with_characters":
                action="walk" if label=="character_walking" else "greeting"
                for name,root,rest,meshes in cast:
                    original=root.location.copy()
                    original_rotation=root.rotation_euler.copy()
                    root.location=(0,0,0)
                    root.rotation_euler.z=0
                    pose_action(root,rest,meshes,bpy.data.actions[f"{name.upper()}_{action.upper()}"],
                                9 if name=="Aarav" else 14,24,action)
                    root.rotation_euler=original_rotation
                    root.location=(original.x,-.65 if action=="walk" else .05,0)
                    bpy.context.view_layer.update()
                    sole=min((bpy.data.objects[f"{name}_Foot_{side}"].matrix_world@Vector(p)).z
                             for side in ("L","R") for p in bpy.data.objects[f"{name}_Foot_{side}"].bound_box)
                    root.location.z=.027-sole
            scene.camera=cameras[label]
            sightlines(scene,cast)
            cast_timings[label]="framing and sightlines pass"
            render(label)
    data={
        "blender":bpy.app.version_string,"engine":scene.render.engine,"resolution":[640,360],
        "build_seconds":round(build_seconds,3),"reload_seconds":round(load_seconds,3),
        "render_seconds":times,"environment_mesh_objects":len(environment),"environment_face_instances":polygons,
        "walk_route_samples":route_checks,"character_views":cast_timings,
    }
    (out/"measurements.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
