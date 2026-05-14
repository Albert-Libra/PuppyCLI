"""Tests for skill manager."""
import tempfile
from pathlib import Path

from puppycli.skill.manager import SkillManager


def _create_test_skill(directory: Path, name: str = "test-skill") -> Path:
    """Helper: create a minimal skill directory with SKILL.md."""
    skill_dir = directory / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A test skill for testing\n---\n\n"
        "# Test Skill\n\nInstructions here.\n",
        encoding="utf-8",
    )
    return skill_dir


def test_list_skills_empty():
    """Listing with no skills should return empty list."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        manager = SkillManager()
        # Override global dir to temp
        manager._global_dir = tmp / "global"
        manager._global_dir.mkdir(parents=True)
        manager._project_dir = tmp / "project"
        manager._project_dir.mkdir(parents=True)

        assert manager.list_skills() == []


def test_install_and_list():
    """Install a skill from path and list it."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = _create_test_skill(tmp, "my-skill")

        manager = SkillManager()
        manager._global_dir = tmp / "skills"
        manager._global_dir.mkdir(parents=True)

        info = manager.install_from_path(source)
        assert info["name"] == "my-skill"
        assert info["location"] == "global"

        skills = manager.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "my-skill"


def test_remove_skill():
    """Remove an installed skill."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = _create_test_skill(tmp, "remove-me")

        manager = SkillManager()
        manager._global_dir = tmp / "skills"
        manager._global_dir.mkdir(parents=True)

        manager.install_from_path(source)
        assert manager.remove_skill("remove-me") is True
        assert manager.list_skills() == []
        assert manager.remove_skill("remove-me") is False  # Already gone


def test_read_skill_content():
    """Read the content of an installed skill."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = _create_test_skill(tmp, "reader-skill")

        manager = SkillManager()
        manager._global_dir = tmp / "skills"
        manager._global_dir.mkdir(parents=True)

        manager.install_from_path(source)
        content = manager.read_skill_content("reader-skill")
        assert content is not None
        assert "name: reader-skill" in content
        assert "Test Skill" in content


def test_parse_frontmatter():
    """Parse YAML frontmatter from SKILL.md."""
    result = SkillManager._parse_frontmatter(
        "---\nname: pdf\ndescription: Process PDFs\n---\n\n# Instructions\n"
    )
    assert result == {"name": "pdf", "description": "Process PDFs"}

    # No frontmatter
    assert SkillManager._parse_frontmatter("# Just markdown") is None
