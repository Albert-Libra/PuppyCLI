"""Skill loader — inject skill metadata and content into agent context."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def collect_skills_metadata(project_dir: Path | None = None) -> list[dict[str, Any]]:
    """Collect skill metadata from global and project-level skill directories.

    Returns a list of {name, description} for injection into the system prompt.
    """
    from puppycli.skill.manager import SkillManager

    manager = SkillManager(project_dir=project_dir)
    skills = manager.list_skills()
    return [{"name": s["name"], "description": s["description"]} for s in skills]


def build_skills_prompt(project_dir: Path | None = None) -> str:
    """Build the skills section of the system prompt.

    Includes available skill metadata and instructions for how to use them.
    """
    from puppycli.skill.manager import SkillManager

    manager = SkillManager(project_dir=project_dir)
    skills = manager.list_skills()

    if not skills:
        return ""

    lines = [
        "",
        "## Available Skills",
        "",
        "You have access to the following Agent Skills. Each skill is a specialized",
        "instruction set that helps you perform specific tasks better.",
        "",
        "| Skill | Description |",
        "|-------|-------------|",
    ]

    for s in skills:
        lines.append(f"| `{s['name']}` | {s['description'][:120]} |")

    lines.extend([
        "",
        "**How to use skills:**",
        "- When a task matches a skill's description, mention that you're using it (e.g., 'Using the `pdf-processing` skill...')",
        "- If you need the full instructions for a skill, you can read them from",
        f"  `<data_dir>/skills/<skill-name>/SKILL.md` or `.puppycli/skills/<skill-name>/SKILL.md`",
        "- Skills may have additional files in `scripts/`, `references/`, and `assets/` directories",
        "",
    ])

    return "\n".join(lines)


def load_skill_content(skill_name: str, project_dir: Path | None = None) -> str | None:
    """Load the full SKILL.md content for a specific skill."""
    from puppycli.skill.manager import SkillManager

    manager = SkillManager(project_dir=project_dir)
    return manager.read_skill_content(skill_name)
