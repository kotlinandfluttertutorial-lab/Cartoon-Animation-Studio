"""Project manager for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from studio.logger import get_logger
from studio.schemas import Project


class ProjectManager:
    """Creates, saves, loads, and lists animation projects."""

    def __init__(self, projects_dir: str | Path) -> None:
        self._projects_dir = Path(projects_dir)
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger("app")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def create_project(
        self, name: str, settings: Optional[dict] = None
    ) -> Project:
        """Create a new project with a unique UUID."""
        project = Project(
            project_name=name,
            settings=settings or {},
        )
        self._logger.info("Created project: %s (%s)", name, project.project_id)
        return project

    def save_project(self, project: Project) -> None:
        """Save project to projects/{project_id}.json.

        If the file already exists, a timestamped backup is created first.
        """
        project_path = self._projects_dir / f"{project.project_id}.json"
        backups_dir = self._projects_dir / "backups"

        if project_path.exists():
            backups_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            backup_path = backups_dir / f"{project.project_id}_{ts}.json"
            shutil.copy2(project_path, backup_path)
            self._logger.debug("Project backup created: %s", backup_path)

        with open(project_path, "w", encoding="utf-8") as f:
            json.dump(project.model_dump(mode="json"), f, indent=2)

        self._logger.info("Project saved: %s", project_path)

    def load_project(self, project_id: str) -> Project:
        """Load a project by its UUID."""
        project_path = self._projects_dir / f"{project_id}.json"
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")

        with open(project_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Project(**data)

    def list_projects(self) -> list[Project]:
        """Return all saved projects sorted by creation date (newest first)."""
        projects: list[Project] = []
        for path in self._projects_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                projects.append(Project(**data))
            except Exception as exc:
                self._logger.warning("Failed to load project %s: %s", path.name, exc)

        projects.sort(key=lambda p: p.creation_date, reverse=True)
        return projects

    def delete_project(self, project_id: str, confirm: bool = True) -> None:
        """Delete a project by ID.

        If confirm=True, raises RuntimeError requiring explicit opt-out.
        Pass confirm=False to actually perform the deletion.
        """
        if confirm:
            raise RuntimeError(
                f"Refusing to delete project '{project_id}' without explicit confirmation. "
                "Call delete_project(project_id, confirm=False) to proceed."
            )

        project_path = self._projects_dir / f"{project_id}.json"
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")

        project_path.unlink()
        self._logger.info("Project deleted: %s", project_id)
