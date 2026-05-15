"""Skill manager — install, remove, list, and scan Skills.

Skills follow the agentskills.io standard: a folder containing SKILL.md
with YAML frontmatter (name, description) and Markdown instructions.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml
import requests


# Paths where skills are stored
PROJECT_SKILLS_DIR_NAME = Path(".puppycli") / "skills"


class SkillManager:
    """Manages installation and discovery of Agent Skills."""

    def __init__(self, project_dir: Path | None = None):
        from puppycli.config import Config

        self._global_dir = Config().base_dir / "skills"
        self._global_dir.mkdir(parents=True, exist_ok=True)
        self._project_dir = project_dir / PROJECT_SKILLS_DIR_NAME if project_dir else None
        if self._project_dir:
            self._project_dir.mkdir(parents=True, exist_ok=True)

    @property
    def project_dir(self) -> Path | None:
        return self._project_dir

    # ---- Discovery ----

    def list_skills(self) -> list[dict[str, Any]]:
        """List all installed skills with metadata.

        Includes adaptation status for each skill.
        """
        skills = []
        seen = set()
        for base in [self._global_dir, self._project_dir]:
            if not base or not base.exists():
                continue
            for d in sorted(base.iterdir()):
                if d.is_dir() and d.name not in seen:
                    info = self._read_skill_info(d)
                    if info:
                        info["location"] = "project" if (self._project_dir and self._project_dir in d.parents) else "global"
                        info["path"] = str(d)
                        # Add adaptation metadata
                        try:
                            from puppycli.skill.adapter import is_adapted
                            info["is_adapted"] = is_adapted(d)
                        except Exception:
                            info["is_adapted"] = False
                        skills.append(info)
                        seen.add(d.name)
        return skills

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """Get a single skill by name."""
        for info in self.list_skills():
            if info["name"] == name:
                return info
        return None

    def get_skill_path(self, name: str) -> Path | None:
        """Get the filesystem path for a skill."""
        for base in [self._project_dir, self._global_dir]:
            if not base:
                continue
            candidate = base / name
            if candidate.is_dir():
                return candidate
        return None

    def read_skill_content(self, name: str) -> str | None:
        """Read the full SKILL.md content for a skill."""
        path = self.get_skill_path(name)
        if not path:
            return None
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            return skill_md.read_text(encoding="utf-8")
        return None

    # ---- Installation ----

    def install_from_path(
        self, source: Path, *, project: bool = False, adapt: bool = True
    ) -> dict[str, Any]:
        """Install a skill from a local directory.

        Args:
            source: Path to the skill directory containing SKILL.md
            project: If True, install to project-level skills directory
            adapt: If True, auto-adapt CLI-oriented skills for PuppyCLI's
                   browser frontend (default: True)
        """
        source = source.resolve()
        info = self._read_skill_info(source)
        if not info:
            raise ValueError(f"No valid SKILL.md found in {source}")
        name = info["name"]

        target_dir = (self._project_dir if project else self._global_dir) / name
        if target_dir.exists():
            raise FileExistsError(f"Skill '{name}' is already installed")

        # Copy entire directory
        shutil.copytree(source, target_dir)

        # ── Frontend adaptation ──
        adaptation_info = None
        if adapt:
            from puppycli.skill.adapter import adapt_skill, analyze_skill

            analysis = analyze_skill(target_dir)
            if analysis["needs_adaptation"]:
                adaptation_info = adapt_skill(target_dir)
                # Refresh skill info after adaptation
                info = self._read_skill_info(target_dir) or info

        info["location"] = "project" if project else "global"
        info["path"] = str(target_dir)
        if adaptation_info:
            info["adaptation"] = adaptation_info
            info["is_adapted"] = adaptation_info.get("status") == "adapted"
        else:
            info["is_adapted"] = False
        return info

    def install_from_github(
        self, repo: str, *, project: bool = False, adapt: bool = True
    ) -> dict[str, Any]:
        """Install a skill from a GitHub repository (owner/repo or full URL).

        Downloads the repo as ZIP and extracts the SKILL.md folder.
        """
        # Normalize repo string
        repo = repo.rstrip("/")
        if repo.startswith("https://github.com/"):
            repo = repo.removeprefix("https://github.com/")
        if repo.startswith("http://github.com/"):
            repo = repo.removeprefix("http://github.com/")

        parts = repo.split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub repo: {repo}. Use format: owner/repo")

        owner, repo_name = parts[0], parts[1]
        zip_url = f"https://github.com/{owner}/{repo_name}/archive/refs/heads/main.zip"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path = tmp_path / "repo.zip"

            # Download
            resp = requests.get(zip_url, timeout=30)
            resp.raise_for_status()
            zip_path.write_bytes(resp.content)

            # Extract
            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)

            # Find the top-level directory (github puts repo-main/)
            extracted = list(extract_dir.iterdir())
            if not extracted:
                raise ValueError("Downloaded ZIP is empty")
            repo_root = extracted[0]

            # Check if root itself is a skill (has SKILL.md)
            if (repo_root / "SKILL.md").exists():
                return self.install_from_path(repo_root, project=project, adapt=adapt)

            # Search for skill directories inside
            for d in repo_root.iterdir():
                if d.is_dir() and (d / "SKILL.md").exists():
                    return self.install_from_path(d, project=project, adapt=adapt)

            # If repo contains a skills/ directory, install all skills
            skills_dir = repo_root / "skills"
            if skills_dir.is_dir():
                installed = []
                for d in skills_dir.iterdir():
                    if d.is_dir() and (d / "SKILL.md").exists():
                        installed.append(self.install_from_path(d, project=project, adapt=adapt))
                if installed:
                    return installed[0]  # Return first for simplicity

            raise ValueError(f"No SKILL.md found in {repo}")

    def install_from_url(
        self, url: str, *, project: bool = False, adapt: bool = True
    ) -> dict[str, Any]:
        """Install a skill from a direct ZIP URL."""
        if "github.com" in url and not url.endswith(".zip"):
            return self.install_from_github(url, project=project, adapt=adapt)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            zip_path = tmp_path / "skill.zip"

            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            zip_path.write_bytes(resp.content)

            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)

            # Search recursively for SKILL.md
            for skill_md_path in sorted(extract_dir.rglob("SKILL.md")):
                skill_dir = skill_md_path.parent
                return self.install_from_path(skill_dir, project=project, adapt=adapt)

            # Maybe the extracted root is a single directory containing SKILL.md
            extracted = list(extract_dir.iterdir())
            if extracted and extracted[0].is_dir() and (extracted[0] / "SKILL.md").exists():
                return self.install_from_path(extracted[0], project=project, adapt=adapt)

            raise ValueError("No SKILL.md found in the downloaded archive")

    # ---- Removal ----

    def remove_skill(self, name: str) -> bool:
        """Remove an installed skill. Returns True if removed."""
        for base in [self._project_dir, self._global_dir]:
            if not base:
                continue
            target = base / name
            if target.is_dir():
                shutil.rmtree(target)
                return True
        return False

    # ---- Adaptation ----

    def adapt_skill(self, name: str) -> dict[str, Any]:
        """Adapt an already-installed skill for PuppyCLI's frontend.

        Useful when a skill was installed before the adapter existed,
        or was installed with adapt=False.
        """
        skill_dir = self.get_skill_path(name)
        if not skill_dir:
            raise ValueError(f"Skill '{name}' not found")

        from puppycli.skill.adapter import adapt_skill as do_adapt

        result = do_adapt(skill_dir)
        if result["status"] == "error":
            raise RuntimeError(result.get("message", "Adaptation failed"))
        return result

    def restore_skill(self, name: str) -> bool:
        """Restore a skill to its original CLI content (revert adaptation)."""
        skill_dir = self.get_skill_path(name)
        if not skill_dir:
            raise ValueError(f"Skill '{name}' not found")

        from puppycli.skill.adapter import restore_original
        return restore_original(skill_dir)

    # ---- Helpers ----

    def _read_skill_info(self, directory: Path) -> dict[str, Any] | None:
        """Parse SKILL.md frontmatter from a directory."""
        skill_md = directory / "SKILL.md"
        if not skill_md.exists():
            return None
        content = skill_md.read_text(encoding="utf-8")
        frontmatter = self._parse_frontmatter(content)
        if not frontmatter or "name" not in frontmatter or "description" not in frontmatter:
            return None
        return {
            "name": frontmatter["name"],
            "description": frontmatter["description"],
            "directory": directory.name,
            "has_scripts": (directory / "scripts").is_dir(),
            "has_references": (directory / "references").is_dir(),
            "has_assets": (directory / "assets").is_dir(),
            "raw_frontmatter": frontmatter,
        }

    @staticmethod
    def _parse_frontmatter(content: str) -> dict[str, Any] | None:
        """Parse YAML frontmatter from SKILL.md content."""
        match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return None
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return None
