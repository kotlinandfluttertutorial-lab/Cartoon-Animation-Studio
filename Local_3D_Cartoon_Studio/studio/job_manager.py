"""Job manager for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from studio.logger import get_logger
from studio.schemas import Job, JobStatus


class JobManager:
    """Creates, updates, and persists animation jobs."""

    def __init__(self, jobs_dir: str | Path) -> None:
        self._jobs_dir = Path(jobs_dir)
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger("jobs")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def create_job(
        self, job_type: str, metadata: Optional[dict] = None
    ) -> Job:
        """Create a new job and persist it immediately."""
        job = Job(
            job_type=job_type,
            metadata=metadata or {},
        )
        self.save_job(job)
        self._logger.info("Created job: %s (type=%s)", job.job_id, job_type)
        return job

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float = 0.0,
        error_message: Optional[str] = None,
    ) -> Job:
        """Update job status and persist."""
        job = self.load_job(job_id)
        job.status = status
        job.progress = progress

        if status == JobStatus.RUNNING and job.start_time is None:
            job.start_time = datetime.utcnow()

        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.end_time = datetime.utcnow()
            if status == JobStatus.COMPLETED:
                job.progress = 1.0

        if error_message is not None:
            job.error_message = error_message

        self.save_job(job)
        self._logger.info(
            "Job %s -> status=%s progress=%.0f%%", job_id, status.value, job.progress * 100
        )
        return job

    def get_job(self, job_id: str) -> Job:
        """Return a job by ID."""
        return self.load_job(job_id)

    def list_jobs(self, status_filter: Optional[JobStatus] = None) -> list[Job]:
        """Return all jobs, optionally filtered by status."""
        jobs: list[Job] = []
        for path in self._jobs_dir.glob("*.json"):
            try:
                job = self.load_job(path.stem)
                if status_filter is None or job.status == status_filter:
                    jobs.append(job)
            except Exception as exc:
                self._logger.warning("Failed to load job %s: %s", path.name, exc)

        jobs.sort(key=lambda j: j.start_time or datetime.min, reverse=True)
        return jobs

    def save_job(self, job: Job) -> None:
        """Persist job to jobs_dir/{job_id}.json."""
        job_path = self._jobs_dir / f"{job.job_id}.json"
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job.model_dump(mode="json"), f, indent=2)

    def load_job(self, job_id: str) -> Job:
        """Load a job from disk by ID."""
        job_path = self._jobs_dir / f"{job_id}.json"
        if not job_path.exists():
            raise FileNotFoundError(f"Job not found: {job_id}")
        with open(job_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Job(**data)

    def recover_interrupted_jobs(self) -> list[str]:
        """Find jobs with status=running and mark them as failed.

        Returns a list of recovered job IDs.
        """
        recovered: list[str] = []
        for path in self._jobs_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("status") == JobStatus.RUNNING.value:
                    job_id = data["job_id"]
                    self.update_status(
                        job_id,
                        JobStatus.FAILED,
                        error_message="Recovered: process interrupted",
                    )
                    recovered.append(job_id)
                    self._logger.warning(
                        "Recovered interrupted job: %s", job_id
                    )
            except Exception as exc:
                self._logger.warning(
                    "Could not inspect job file %s: %s", path.name, exc
                )

        return recovered
