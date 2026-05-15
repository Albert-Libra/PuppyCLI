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


# ── Adapter tests ──


def test_analyze_cli_skill():
    """Analyze a CLI-oriented skill and detect indicators."""
    from puppycli.skill.adapter import analyze_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "cli-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: cli-skill\ndescription: A CLI tool skill\n---\n\n"
            "# CLI Skill\n\n"
            "Use the Bash tool to run shell commands.\n"
            "Use Read to read files.\n"
            "Use Write to write files.\n"
            "Use Grep to search content.\n",
            encoding="utf-8",
        )

        analysis = analyze_skill(skill_dir)
        assert analysis["is_cli_oriented"] is True
        assert analysis["needs_adaptation"] is True
        assert len(analysis["tool_references"]) >= 3
        assert "Bash" in analysis["tool_references"] or "bash" in analysis["tool_references"]


def test_analyze_non_cli_skill():
    """A non-CLI skill should not need adaptation."""
    from puppycli.skill.adapter import analyze_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "web-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: web-search\ndescription: Search the web\n---\n\n"
            "# Web Search Skill\n\n"
            "Use web_search to find information.\n"
            "Use web_fetch to extract page content.\n",
            encoding="utf-8",
        )

        analysis = analyze_skill(skill_dir)
        assert analysis["needs_adaptation"] is False


def test_adapt_skill():
    """Adapt a CLI skill and verify the result."""
    from puppycli.skill.adapter import adapt_skill, is_adapted

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "cli-skill"
        skill_dir.mkdir()
        original_content = (
            "---\nname: cli-skill\ndescription: A CLI tool skill\n---\n\n"
            "# CLI Skill\n\n"
            "Use the Bash tool to run shell commands.\n"
            "Use Read to read files and Write to write files.\n"
        )
        (skill_dir / "SKILL.md").write_text(original_content, encoding="utf-8")

        result = adapt_skill(skill_dir)
        assert result["status"] == "adapted"
        assert is_adapted(skill_dir) is True

        # Verify backup was created
        assert (skill_dir / "SKILL.md.orig").exists()
        backup_content = (skill_dir / "SKILL.md.orig").read_text(encoding="utf-8")
        assert backup_content == original_content

        # Verify adapted content
        adapted_content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "PuppyCLI Environment (auto-adapted)" in adapted_content
        assert "Bash" not in adapted_content or "run_powershell" in adapted_content


def test_adapt_skill_idempotent():
    """Adapting an already-adapted skill should be skipped."""
    from puppycli.skill.adapter import adapt_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "cli-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: cli-skill\ndescription: A CLI tool skill\n---\n\n"
            "# CLI Skill\n\nUse the Bash tool.\n",
            encoding="utf-8",
        )

        result1 = adapt_skill(skill_dir)
        assert result1["status"] == "adapted"

        result2 = adapt_skill(skill_dir)
        assert result2["status"] == "skipped"
        assert "already adapted" in result2["message"]


def test_restore_original():
    """Restore a skill to its original content."""
    from puppycli.skill.adapter import adapt_skill, restore_original, is_adapted

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "cli-skill"
        skill_dir.mkdir()
        original_content = (
            "---\nname: cli-skill\ndescription: A CLI tool skill\n---\n\n"
            "# CLI Skill\n\nUse the Bash tool.\n"
        )
        (skill_dir / "SKILL.md").write_text(original_content, encoding="utf-8")

        adapt_skill(skill_dir)
        assert is_adapted(skill_dir) is True

        restored = restore_original(skill_dir)
        assert restored is True
        assert is_adapted(skill_dir) is False
        assert not (skill_dir / "SKILL.md.orig").exists()

        current = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert current == original_content


def test_adapt_skill_dry_run():
    """Dry run should not modify files."""
    from puppycli.skill.adapter import adapt_skill, is_adapted

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "cli-skill"
        skill_dir.mkdir()
        original = (
            "---\nname: cli-skill\ndescription: A CLI tool skill\n---\n\n"
            "# CLI Skill\nUse the Bash tool.\n"
        )
        (skill_dir / "SKILL.md").write_text(original, encoding="utf-8")

        result = adapt_skill(skill_dir, dry_run=True)
        assert result["status"] == "would_adapt"
        assert is_adapted(skill_dir) is False
        assert not (skill_dir / "SKILL.md.orig").exists()
        assert (skill_dir / "SKILL.md").read_text(encoding="utf-8") == original


def test_install_with_adaptation():
    """Installing a CLI skill should auto-adapt."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = tmp / "cli-skill"
        source.mkdir()
        (source / "SKILL.md").write_text(
            "---\nname: cli-tool\ndescription: A CLI-oriented skill\n---\n\n"
            "# CLI Tool\n\n"
            "Use Bash to run commands. Use Read to read files.\n"
            "Use Write to write files. Use Grep to search.\n"
            "This tool works from the command line.\n",
            encoding="utf-8",
        )

        manager = SkillManager()
        manager._global_dir = tmp / "skills"
        manager._global_dir.mkdir(parents=True)

        info = manager.install_from_path(source, adapt=True)
        assert info["is_adapted"] is True
        assert info["name"] == "cli-tool"

        # Read the installed skill content
        content = manager.read_skill_content("cli-tool")
        assert "PuppyCLI Environment (auto-adapted)" in content
        assert "run_powershell" in content


def test_install_without_adaptation():
    """Installing with adapt=False should preserve original content."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = tmp / "cli-skill"
        source.mkdir()
        original = (
            "---\nname: cli-raw\ndescription: A CLI skill\n---\n\n"
            "Use Bash to run commands.\n"
        )
        (source / "SKILL.md").write_text(original, encoding="utf-8")

        manager = SkillManager()
        manager._global_dir = tmp / "skills"
        manager._global_dir.mkdir(parents=True)

        info = manager.install_from_path(source, adapt=False)
        assert info["is_adapted"] is False

        content = manager.read_skill_content("cli-raw")
        assert "PuppyCLI Environment" not in content
        assert "Use Bash to run commands" in content


def test_manager_adapt_and_restore():
    """Test the SkillManager adapt_skill and restore_skill methods."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        source = tmp / "cli-skill"
        source.mkdir()
        (source / "SKILL.md").write_text(
            "---\nname: manager-test\ndescription: Test skill\n---\n\n"
            "Use Bash to run commands.\n",
            encoding="utf-8",
        )

        manager = SkillManager()
        manager._global_dir = tmp / "skills"
        manager._global_dir.mkdir(parents=True)

        # Install without adaptation
        info = manager.install_from_path(source, adapt=False)
        assert info["is_adapted"] is False

        # Adapt later
        result = manager.adapt_skill("manager-test")
        assert result["status"] == "adapted"

        # Verify adapted
        content = manager.read_skill_content("manager-test")
        assert "PuppyCLI Environment" in content

        # Restore
        restored = manager.restore_skill("manager-test")
        assert restored is True

        content = manager.read_skill_content("manager-test")
        assert "PuppyCLI Environment" not in content
        assert "Use Bash to run commands" in content


# ── Interaction adaptation tests ──


def test_analyze_interaction_skill():
    """A skill with AskUserQuestion should be detected as CLI-oriented."""
    from puppycli.skill.adapter import analyze_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "qa-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: qa-skill\ndescription: Asks questions\n---\n\n"
            "# QA Skill\n\n"
            "Use AskUserQuestion to present options to the user.\n"
            "Set multiSelect: true when the user can pick multiple.\n",
            encoding="utf-8",
        )

        analysis = analyze_skill(skill_dir)
        assert analysis["is_cli_oriented"] is True
        assert analysis["needs_adaptation"] is True
        assert "AskUserQuestion" in analysis["tool_references"]


def test_adapt_interaction_skill():
    """AskUserQuestion references should be translated to chat guidance."""
    from puppycli.skill.adapter import adapt_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "qa-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: qa-skill\ndescription: Asks questions\n---\n\n"
            "# QA Skill\n\n"
            "Use AskUserQuestion to present options to the user.\n"
            "The user can pick from the list.\n",
            encoding="utf-8",
        )

        result = adapt_skill(skill_dir)
        assert result["status"] == "adapted"

        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        # Preamble teaches interaction patterns
        assert "User Interaction" in content
        # Body (after preamble) must not have unresolved sentinels
        assert "__PUPPYCLI_" not in content
        # Body should contain the resolved guidance text
        assert "clearly formatted choice in chat" in content


def test_adapt_confirm_action():
    """ConfirmAction references should be translated to yes/no pattern."""
    from puppycli.skill.adapter import adapt_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "confirm-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: confirm-skill\ndescription: Confirms actions\n---\n\n"
            "# Confirm Skill\n\n"
            "Use ConfirmAction before deleting files.\n",
            encoding="utf-8",
        )

        result = adapt_skill(skill_dir)
        assert result["status"] == "adapted"

        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        # No unresolved sentinels
        assert "__PUPPYCLI_" not in content
        # Should contain yes/no confirmation guidance (in preamble or body)
        assert ("yes" in content.lower() and "no" in content.lower()) or \
               "confirm" in content.lower()


def test_adapt_select_option():
    """SelectOption references should be translated to numbered list pattern."""
    from puppycli.skill.adapter import adapt_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "select-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: select-skill\ndescription: Lets user select\n---\n\n"
            "# Select Skill\n\n"
            "Use SelectOption to let the user choose from available items.\n",
            encoding="utf-8",
        )

        result = adapt_skill(skill_dir)
        assert result["status"] == "adapted"

        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        # No unresolved sentinels
        assert "__PUPPYCLI_" not in content
        # Should contain numbered list guidance
        assert "numbered list" in content.lower()


def test_adapt_ask_user_input():
    """AskUserInput references should be translated to text input pattern."""
    from puppycli.skill.adapter import adapt_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "input-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: input-skill\ndescription: Asks for input\n---\n\n"
            "# Input Skill\n\n"
            "Use AskUserInput to get text from the user.\n",
            encoding="utf-8",
        )

        result = adapt_skill(skill_dir)
        assert result["status"] == "adapted"

        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "AskUserInput" not in content
        assert "type their input" in content.lower() or "type your answer" in content.lower()


def test_preamble_contains_interaction_patterns():
    """Adapted skill preamble must teach the 3 interaction patterns."""
    from puppycli.skill.adapter import adapt_skill

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        skill_dir = tmp / "any-cli-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: any-skill\ndescription: Some skill\n---\n\n"
            "Use Bash to run things.\n",
            encoding="utf-8",
        )

        adapt_skill(skill_dir)
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

        # Preamble should teach all 3 patterns
        assert "Pattern 1" in content or "Ask the user to choose" in content
        assert "Pattern 2" in content or "text input" in content
        assert "Pattern 3" in content or "confirm" in content.lower()
        # Should explicitly forbid calling AskUserQuestion
        assert "NEVER call a function named AskUserQuestion" in content
        # Should mention multiSelect handling
        assert "multiSelect" in content or "more than one" in content
