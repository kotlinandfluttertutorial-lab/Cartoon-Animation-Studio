"""Unit tests for project_manager.py."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.project_manager import ProjectManager
from studio.schemas import Project


class TestCreateProject(unittest.TestCase):
    def test_create_project(self):
        """create_project returns a Project with a valid UUID."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(tmp)
            project = mgr.create_project("Test Project")

        self.assertIsInstance(project, Project)
        self.assertEqual(project.project_name, "Test Project")
        # UUID should be a 36-character string
        self.assertEqual(len(project.project_id), 36)
        self.assertEqual(project.project_id.count("-"), 4)


class TestSaveAndLoad(unittest.TestCase):
    def test_save_and_load(self):
        """save then load returns an identical project."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(tmp)
            project = mgr.create_project("Save/Load Test", settings={"fps": 12})
            mgr.save_project(project)
            loaded = mgr.load_project(project.project_id)

        self.assertEqual(loaded.project_id, project.project_id)
        self.assertEqual(loaded.project_name, project.project_name)
        self.assertEqual(loaded.settings, project.settings)


class TestListProjects(unittest.TestCase):
    def test_list_projects(self):
        """create 3 projects, list returns all 3."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(tmp)
            for i in range(3):
                p = mgr.create_project(f"Project {i}")
                mgr.save_project(p)
            projects = mgr.list_projects()

        self.assertEqual(len(projects), 3)


class TestBackupOnOverwrite(unittest.TestCase):
    def test_backup_on_overwrite(self):
        """Saving the same project_id twice creates a backup file."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(tmp)
            project = mgr.create_project("Backup Test")
            mgr.save_project(project)  # first save
            mgr.save_project(project)  # second save should create backup

            backups_dir = Path(tmp) / "backups"
            backups = list(backups_dir.glob(f"{project.project_id}_*.json"))

        self.assertGreater(len(backups), 0, "No backup file was created on second save")


class TestDeleteRequiresConfirm(unittest.TestCase):
    def test_delete_requires_confirm(self):
        """delete_project without confirm=False raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = ProjectManager(tmp)
            project = mgr.create_project("Delete Test")
            mgr.save_project(project)

            with self.assertRaises(RuntimeError):
                mgr.delete_project(project.project_id)  # confirm=True by default


if __name__ == "__main__":
    unittest.main()
