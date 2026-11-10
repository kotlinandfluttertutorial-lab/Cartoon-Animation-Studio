"""Pydantic v2 schemas for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderProfile(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    engine: str
    image_format: str
    shading: str
    enabled: bool = True
    ffmpeg_output: bool = False


class AppSettings(BaseModel):
    blender_executable: str
    ffmpeg_executable: str
    ffprobe_executable: str
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    output_dir: str
    projects_dir: str
    logs_dir: str
    process_timeout_seconds: int = Field(default=3600, gt=0)
    active_render_profile: str = "PREVIEW"

    @field_validator("blender_executable", "ffmpeg_executable", "ffprobe_executable")
    @classmethod
    def validate_executable_path(cls, v: str) -> str:
        p = Path(v)
        if not p.exists():
            raise ValueError(f"Executable not found: {v}")
        return str(p)


class Project(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str
    creation_date: datetime = Field(default_factory=datetime.utcnow)
    settings: dict[str, Any] = Field(default_factory=dict)
    scenes: list[str] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    output_files: list[str] = Field(default_factory=list)


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str
    status: JobStatus = JobStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    blender_log: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemInfo(BaseModel):
    cpu: str
    ram_gb: float
    gpu: str
    blender_version: str
    ffmpeg_version: str
    python_version: str
    platform: str
