"""Unit tests for job_manager.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.job_manager import JobManager
from studio.schemas import Job, JobStatus


class TestCreateJob(unittest.TestCase):
    def test_create_job(self):
        """create_job returns a Job with status=pending."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = JobManager(tmp)
            job = mgr.create_job("render", metadata={"scene": "test"})

        self.assertIsInstance(job, Job)
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.job_type, "render")
        self.assertEqual(job.metadata["scene"], "test")


class TestStatusTransitions(unittest.TestCase):
    def test_status_transitions(self):
        """pending -> running -> completed transitions work correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = JobManager(tmp)
            job = mgr.create_job("encode")

            mgr.update_status(job.job_id, JobStatus.RUNNING)
            loaded = mgr.get_job(job.job_id)
            self.assertEqual(loaded.status, JobStatus.RUNNING)
            self.assertIsNotNone(loaded.start_time)

            mgr.update_status(job.job_id, JobStatus.COMPLETED, progress=1.0)
            loaded = mgr.get_job(job.job_id)
            self.assertEqual(loaded.status, JobStatus.COMPLETED)
            self.assertEqual(loaded.progress, 1.0)
            self.assertIsNotNone(loaded.end_time)


class TestFailedStatus(unittest.TestCase):
    def test_failed_status(self):
        """update to failed with error_message persists correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = JobManager(tmp)
            job = mgr.create_job("render")
            mgr.update_status(
                job.job_id,
                JobStatus.FAILED,
                error_message="Out of memory",
            )
            loaded = mgr.get_job(job.job_id)

        self.assertEqual(loaded.status, JobStatus.FAILED)
        self.assertEqual(loaded.error_message, "Out of memory")


class TestRecoverInterrupted(unittest.TestCase):
    def test_recover_interrupted(self):
        """Job with status=running in JSON is recovered and returned in list."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = JobManager(tmp)
            job = mgr.create_job("render")

            # Manually set status to running in the JSON file
            job_path = Path(tmp) / f"{job.job_id}.json"
            with open(job_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["status"] = "running"
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            recovered = mgr.recover_interrupted_jobs()

        self.assertIn(job.job_id, recovered)


class TestListJobsFilter(unittest.TestCase):
    def test_list_jobs_filter(self):
        """Filter by status returns only matching jobs."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = JobManager(tmp)
            j1 = mgr.create_job("render")
            j2 = mgr.create_job("encode")
            j3 = mgr.create_job("export")

            mgr.update_status(j1.job_id, JobStatus.COMPLETED)
            mgr.update_status(j2.job_id, JobStatus.RUNNING)
            # j3 stays pending

            completed = mgr.list_jobs(status_filter=JobStatus.COMPLETED)
            pending = mgr.list_jobs(status_filter=JobStatus.PENDING)
            all_jobs = mgr.list_jobs()

        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].job_id, j1.job_id)
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(all_jobs), 3)


class TestPersistence(unittest.TestCase):
    def test_persistence(self):
        """save and reload job from disk returns identical data."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = JobManager(tmp)
            job = mgr.create_job("render", metadata={"frame_count": 60})
            mgr.update_status(job.job_id, JobStatus.RUNNING)

            # Reload from disk
            loaded = mgr.load_job(job.job_id)

        self.assertEqual(loaded.job_id, job.job_id)
        self.assertEqual(loaded.status, JobStatus.RUNNING)
        self.assertEqual(loaded.metadata["frame_count"], 60)


if __name__ == "__main__":
    unittest.main()
