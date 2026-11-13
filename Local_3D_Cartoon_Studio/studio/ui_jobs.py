"""Persistent job state for the localhost Streamlit studio."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

import psutil

from studio.story_render import PROJECT, atomic_json, input_file, read_inputs

LOCK = threading.Lock()
COMMANDS = {"plan": "stage5_story.py", "audio": "stage5_story.py", "render": "stage6_render.py"}


def project_path(root, name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", name) or re.fullmatch(
        r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", name, re.IGNORECASE
    ):
        raise ValueError("Use up to 48 letters, numbers, hyphens, or underscores for the project name.")
    path = root / name
    if path.resolve().parent != root.resolve() or path.is_symlink():
        raise ValueError("The project directory must be inside the local studio workspace.")
    return path


def new_directory(parent):
    return parent / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def job_status(job):
    result = read_json(job / "result.json")
    if result:
        return result
    worker = read_json(job / "worker.json")
    if worker:
        try:
            process = psutil.Process(worker["pid"])
            if abs(process.create_time() - worker["created"]) < 0.01 and process.is_running():
                return {"status": "running"}
        except psutil.NoSuchProcess:
            pass
    return {"status": "interrupted", "message": "The worker stopped before recording a result."}


def jobs(project):
    for path in sorted((project / "jobs").glob("*/job.json"), reverse=True):
        job = read_json(path)
        if job:
            yield path.parent, job, job_status(path.parent)


def start_job(project, kind, arguments, output):
    with LOCK:
        if any(result["status"] == "running" for _, _, result in jobs(project)):
            raise ValueError("Wait for the active project job to finish.")
        directory = new_directory(project / "jobs")
        directory.mkdir(parents=True)
        atomic_json(directory / "job.json", {
            "kind": kind, "args": [str(arg) for arg in arguments], "output": str(output),
        })
        try:
            worker = subprocess.Popen(
                [sys.executable, "-m", "studio.ui_jobs", str(directory)],
                cwd=PROJECT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                created = psutil.Process(worker.pid).create_time()
            except psutil.NoSuchProcess:
                created = time.time()
            atomic_json(directory / "worker.json", {"pid": worker.pid, "created": created})
        except OSError as exc:
            atomic_json(directory / "result.json", {"status": "failed", "message": str(exc)})
            raise
    return directory


def import_prepared(source, target):
    source = source.resolve()
    _, _, scenes, dependencies = read_inputs(source)
    paths = {path for path in dependencies if path.is_relative_to(source)}
    for _, _, lines in scenes:
        for line in lines:
            paths.add(input_file(source, line["audio"]))
    target.mkdir(parents=True)
    for path in sorted(paths, key=lambda path: path.name == "timing.json"):
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def verify_result(kind, output):
    if kind == "plan":
        if (output / "story.json").is_file():
            return {"status": "complete"}
    elif kind == "audio":
        if (output / "timing.json").is_file():
            return {"status": "complete"}
    else:
        report = read_json(output / "production_report.json")
        final = output / "final_video.mp4"
        if report.get("status") == "complete" and final.is_file() and final.stat().st_size > 0:
            return {"status": "complete"}
        if (output / "progress.json").is_file() and not final.exists():
            return {"status": "paused"}
    return {"status": "failed", "message": "The command did not produce the expected result."}


def execute_job(directory):
    job = read_json(directory / "job.json")
    try:
        with (directory / "process.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [sys.executable, str(PROJECT / COMMANDS[job["kind"]]), *job["args"]],
                cwd=PROJECT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            )
        if result.returncode:
            state = {"status": "failed", "message": f"The command exited with code {result.returncode}. See the job log."}
        else:
            state = verify_result(job["kind"], Path(job["output"]))
    except (OSError, ValueError, KeyError) as exc:
        state = {"status": "failed", "message": str(exc)}
    atomic_json(directory / "result.json", state)


if __name__ == "__main__":
    execute_job(Path(sys.argv[1]))
