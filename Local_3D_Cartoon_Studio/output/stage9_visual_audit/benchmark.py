import json, os, subprocess, time
from pathlib import Path
import psutil
out=Path(os.environ["STAGE9_OUT"])
blender=os.environ["STAGE9_BLENDER"]
cases=[
    ("BLENDER_WORKBENCH",640,12,12,"workbench_360p_12"),
    ("BLENDER_WORKBENCH",640,24,24,"workbench_360p_24"),
    ("BLENDER_WORKBENCH",1280,24,24,"workbench_720p_24"),
    ("BLENDER_EEVEE_NEXT",640,24,1,"eevee_background"),
    ("CYCLES",640,24,1,"cycles_cpu"),
]
for engine,w,fps,count,tag in cases:
    cmd=[blender,"-b",str(out/"comparison.blend"),"-t","6","--python-exit-code","1","--python",str(out/"audit_scene.py"),
         "--",engine,str(w),str(fps),str(count),tag]
    start=time.perf_counter()
    peak=0
    timed_out=False
    with (out/f"{tag}.log").open("w",encoding="utf-8") as log:
        child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
        proc=psutil.Process(child.pid)
        while child.poll() is None:
            try:
                peak=max(peak,proc.memory_info().rss)
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                pass
            if time.perf_counter()-start>180:
                timed_out=True
                child.kill()
                child.wait()
                break
            time.sleep(.05)
    result=dict(command=cmd,exit_code=child.returncode,wall_seconds=round(time.perf_counter()-start,3),
                peak_rss_mib=round(peak/2**20,2) if peak else None,timed_out=timed_out)
    (out/f"{tag}.process.json").write_text(json.dumps(result,indent=2))
    print(tag, result["exit_code"],result["wall_seconds"],result["peak_rss_mib"],flush=True)
