"""Skill adapter — transforms CLI-oriented skills for PuppyCLI's browser frontend.

Many open-source Agent Skills are designed for CLI-based coding assistants
(Claude Code, Codex, Cursor, etc.). They reference tools (Bash, Read, Edit,
Grep, Glob) and concepts that don't exist in PuppyCLI's browser-based chat UI.

This module analyzes and transforms SKILL.md content so skills work correctly
in PuppyCLI's environment with its available tools (run_powershell, web_search,
web_fetch, search_knowledge, process_pdf_file).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ──────────────────────────────────────────────────────────────────────
# Tool name mapping: CLI-tool references → PuppyCLI equivalents
# ──────────────────────────────────────────────────────────────────────

_TOOL_MAP: dict[str, str] = {
    # Shell execution
    "bash": "run_powershell",
    "Bash": "run_powershell",
    "shell": "run_powershell",
    "Shell": "run_powershell",
    "Terminal": "run_powershell",
    "run_shell": "run_powershell",
    "execute_command": "run_powershell",
    "run_terminal_cmd": "run_powershell",
    # File reading
    "Read": "run_powershell (via Get-Content)",
    "read_file": "run_powershell (via Get-Content)",
    "cat": "run_powershell (via Get-Content)",
    # File writing
    "Write": "run_powershell (via Set-Content / Out-File)",
    "write_file": "run_powershell (via Set-Content / Out-File)",
    "write_to_file": "run_powershell (via Set-Content / Out-File)",
    # File editing
    "Edit": "run_powershell (via file-editing cmdlets)",
    "edit_file": "run_powershell (via file-editing cmdlets)",
    "replace_in_file": "run_powershell (via file-editing cmdlets)",
    # File search / glob
    "Glob": "run_powershell (via Get-ChildItem)",
    "glob": "run_powershell (via Get-ChildItem)",
    "find": "run_powershell (via Get-ChildItem)",
    "list_files": "run_powershell (via Get-ChildItem)",
    # Content search
    "Grep": "run_powershell (via Select-String)",
    "grep": "run_powershell (via Select-String)",
    "ripgrep": "run_powershell (via Select-String)",
    "rg": "run_powershell (via Select-String)",
    "search_content": "run_powershell (via Select-String)",
    "search_file": "run_powershell (via Select-String)",
    # Web (keep same, just normalize)
    "WebSearch": "web_search",
    "WebFetch": "web_fetch",
    # Task / sub-agent
    "Task": "delegate to new agent instance (not available; perform task directly)",
    "task": "delegate to new agent instance (not available; perform task directly)",
    # ── User interaction tools ──
    # These are mapped to a sentinel that _adapt_body detects and replaces
    # with a Markdown interaction pattern block (see _INTERACTION_SENTINEL).
    "AskUserQuestion": "__PUPPYCLI_ASK_USER__",
    "ask_user_question": "__PUPPYCLI_ASK_USER__",
    "ask_user": "__PUPPYCLI_ASK_USER__",
    "AskUserInput": "__PUPPYCLI_ASK_INPUT__",
    "ask_user_input": "__PUPPYCLI_ASK_INPUT__",
    "prompt_user": "__PUPPYCLI_ASK_INPUT__",
    "ConfirmAction": "__PUPPYCLI_ASK_CONFIRM__",
    "confirm_action": "__PUPPYCLI_ASK_CONFIRM__",
    "SelectOption": "__PUPPYCLI_ASK_SELECT__",
    "select_option": "__PUPPYCLI_ASK_SELECT__",
    "SelectFromList": "__PUPPYCLI_ASK_SELECT__",
    "AskUser": "__PUPPYCLI_ASK_USER__",
}

# Sentinels that _adapt_body replaces with rich Markdown interaction guides
_INTERACTION_SENTINELS: dict[str, str] = {
    "__PUPPYCLI_ASK_USER__": (
        "present the user with a **clearly formatted choice in chat**"
    ),
    "__PUPPYCLI_ASK_INPUT__": (
        "ask the user to type their input in the chat"
    ),
    "__PUPPYCLI_ASK_CONFIRM__": (
        "ask the user to confirm by typing **yes** or **no** in chat"
    ),
    "__PUPPYCLI_ASK_SELECT__": (
        "present a numbered list of options in chat for the user to choose from"
    ),
}

# ──────────────────────────────────────────────────────────────────────
# Terminology mapping: CLI concepts → browser chat concepts
# ──────────────────────────────────────────────────────────────────────

_TERM_REPLACEMENTS: list[tuple[str, str]] = [
    (r'\bterminal\b', 'chat interface'),
    (r'\bTerminal\b', 'Chat interface'),
    (r'\bcommand line\b', 'chat interface'),
    (r'\bcommand-line\b', 'chat interface'),
    (r'\bCLI\b', 'GUI'),
    (r'\bstdout\b', 'output'),
    (r'\bstderr\b', 'error output'),
    (r'\bprint to console\b', 'display in chat'),
    (r'\bconsole output\b', 'chat message'),
    (r'\bUnix-like\b', 'Windows'),
    (r'\bunix\b', 'Windows'),
]

# ──────────────────────────────────────────────────────────────────────
# Patterns that mark a skill as CLI-oriented
# ──────────────────────────────────────────────────────────────────────

_CLI_INDICATORS: list[str] = [
    r'\bBash\b',
    r'\bRead\b.*tool',
    r'\bWrite\b.*tool',
    r'\bEdit\b.*tool',
    r'\bGlob\b.*tool',
    r'\bGrep\b.*tool',
    r'\bstock bash',
    r'\bunix\b',
    r'\bcommand[- ]line\b',
    # Interaction patterns
    r'\bAskUserQuestion\b',
    r'\bConfirmAction\b',
    r'\bSelectOption\b',
    r'\bAskUserInput\b',
    r'\bSelectFromList\b',
    r'\bmultiSelect\b',
    r'\bmulti_select\b',
]

# ──────────────────────────────────────────────────────────────────────
# PuppyCLI environment preamble injected into adapted skills
# ──────────────────────────────────────────────────────────────────────

_PUPPYCLI_PREAMBLE = """## PuppyCLI Environment (auto-adapted)

> This skill was **automatically adapted** for PuppyCLI's browser-based chat
> interface. Original CLI-oriented instructions have been translated to work
> with PuppyCLI's available tools.

**You are a browser-based AI assistant**, not a terminal-based one. The user
interacts with you through a web chat with full Markdown/LaTeX rendering.
You CAN display images using `![desc](/api/file?path=<absolute_path>)`.

**Your available tools:**
| Tool | Purpose |
|------|---------|
| `run_powershell` | Execute PowerShell commands on Windows (use for ALL file ops, system commands, etc.) |
| `web_search` | Search the web via DuckDuckGo |
| `web_fetch` | Extract text from a URL |
| `search_knowledge` | Search user's personal knowledge base |
| `process_pdf_file` | Extract text from PDFs into knowledge base |

**Key differences from CLI-based assistants:**
- You do NOT have dedicated `Read`, `Write`, `Edit`, `Glob`, or `Grep` tools.
  Instead, use `run_powershell` with the appropriate PowerShell cmdlet:
  - Read a file: `Get-Content <path>`
  - Write to a file: `Set-Content <path> <value>` or `Out-File`
  - List files: `Get-ChildItem <path>`
  - Search content: `Select-String -Path <path> -Pattern <regex>`
- This is a **Windows** environment. Use PowerShell syntax, not bash.
- The user sees formatted Markdown. Use rich formatting to present results.
- You cannot directly edit files in-place. Read → modify → write back.
- Images work: `![alt text](/api/file?path=C:/path/to/image.png)`

### User Interaction (no AskUserQuestion tool)

You do NOT have `AskUserQuestion`, `ConfirmAction`, or `SelectOption`
functions.  When the skill tells you to ask the user something, use
**Markdown in the chat** instead.  The user will read your formatted
message and type their answer.

**Pattern 1 — Ask the user to choose from options:**

```
**Please choose:**

| # | Option | What it means |
|---|--------|---------------|
| A | [label] | [short description] |
| B | [label] | [short description] |
| C | [label] | [short description] |

Reply with the letter (A/B/C) or describe your preference.
```

> If the original skill has `multiSelect: true`, say:
> "You can pick **more than one**. Reply with letters (e.g. A+C) or describe."

**Pattern 2 — Ask the user for text input:**

```
**I need more information:**

[Ask a clear, specific question here.]

Please type your answer in the chat.
```

**Pattern 3 — Ask the user to confirm an action:**

```
**About to [describe action]:**
- [list what will happen]
- [note any risks]

Reply **yes** to proceed, or **no** to cancel.
```

**Rules for interaction:**
- NEVER call a function named AskUserQuestion — it does not exist.
- ALWAYS format choices as a Markdown table or numbered list.
- After presenting options, STOP and wait for the user's reply.
- Parse the user's text reply — accept letters, numbers, or natural language.
- If the user's reply is ambiguous, ask for clarification with concrete options.

**Original skill instructions follow below.**

---
"""

# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def analyze_skill(skill_dir: Path) -> dict[str, Any]:
    """Analyze a skill directory and return adaptation diagnostics.

    Returns a dict with:
        is_cli_oriented: bool — whether the skill appears designed for CLI tools
        indicators: list[str] — which CLI patterns were detected
        tool_references: list[str] — tool names found in the SKILL.md
        needs_adaptation: bool — whether adaptation is recommended
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {
            "is_cli_oriented": False,
            "indicators": [],
            "tool_references": [],
            "needs_adaptation": False,
            "error": "No SKILL.md found",
        }

    content = skill_md.read_text(encoding="utf-8")

    # Check for CLI indicators
    indicators = []
    for pattern in _CLI_INDICATORS:
        if re.search(pattern, content):
            # Clean up pattern for display
            clean = pattern.replace(r'\b', '').replace(r'\[-', '-').replace(r'\]', '')
            indicators.append(clean)

    # Find tool references
    tool_refs = set()
    for tool_name in _TOOL_MAP:
        if re.search(r'\b' + re.escape(tool_name) + r'\b', content):
            tool_refs.add(tool_name)

    is_cli = len(indicators) >= 1 or len(tool_refs) >= 2

    return {
        "is_cli_oriented": is_cli,
        "indicators": sorted(indicators),
        "tool_references": sorted(tool_refs),
        "needs_adaptation": is_cli,
    }


def adapt_skill(skill_dir: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Adapt a skill for PuppyCLI's browser frontend.

    Modifies SKILL.md in-place:
    1. Backs up original as SKILL.md.orig (if not already backed up)
    2. Prepends PuppyCLI environment preamble
    3. Translates tool references and terminology
    4. Updates frontmatter with adaptation metadata

    Args:
        skill_dir: Path to the skill directory containing SKILL.md
        dry_run: If True, return what would be done without modifying files

    Returns:
        A dict with adaptation result info.
    """
    skill_md = skill_dir / "SKILL.md"
    orig_backup = skill_dir / "SKILL.md.orig"

    if not skill_md.exists():
        return {"status": "error", "message": "No SKILL.md found"}

    # Read current content
    original_content = skill_md.read_text(encoding="utf-8")

    # Analyze
    analysis = analyze_skill(skill_dir)

    if not analysis["needs_adaptation"]:
        return {
            "status": "skipped",
            "message": "Skill does not appear CLI-oriented; no adaptation needed",
            "analysis": analysis,
        }

    # Already adapted?
    if "PuppyCLI Environment (auto-adapted)" in original_content:
        return {
            "status": "skipped",
            "message": "Skill already adapted for PuppyCLI",
            "analysis": analysis,
        }

    if dry_run:
        return {
            "status": "would_adapt",
            "message": f"Would adapt skill (detected {len(analysis['indicators'])} CLI indicators, "
                       f"{len(analysis['tool_references'])} tool references)",
            "analysis": analysis,
        }

    # ── Perform adaptation ──

    # 1. Back up original
    if not orig_backup.exists():
        orig_backup.write_text(original_content, encoding="utf-8")

    # 2. Strip leading YAML frontmatter, adapt it, then reattach
    adapted_body = _adapt_body(original_content)

    # 3. Enhance frontmatter
    adapted_content = _enhance_frontmatter(adapted_body)

    # 4. Prepend PuppyCLI preamble
    adapted_content = _PUPPYCLI_PREAMBLE + adapted_content

    # 5. Write adapted version
    skill_md.write_text(adapted_content, encoding="utf-8")

    return {
        "status": "adapted",
        "message": f"Skill adapted: {len(analysis['indicators'])} CLI indicators and "
                   f"{len(analysis['tool_references'])} tool references translated",
        "analysis": analysis,
        "backup_created": orig_backup.exists(),
    }


def restore_original(skill_dir: Path) -> bool:
    """Restore the original SKILL.md from SKILL.md.orig backup."""
    orig = skill_dir / "SKILL.md.orig"
    skill_md = skill_dir / "SKILL.md"

    if not orig.exists():
        return False

    skill_md.write_text(orig.read_text(encoding="utf-8"), encoding="utf-8")
    orig.unlink()
    return True


def is_adapted(skill_dir: Path) -> bool:
    """Check whether a skill has been adapted for PuppyCLI."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False
    return "PuppyCLI Environment (auto-adapted)" in skill_md.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────


def _adapt_body(content: str) -> str:
    """Apply tool name and terminology translations to skill body text.

    Preserves YAML frontmatter, adapting only the Markdown body.
    Also resolves interaction sentinels into readable guidance.
    """
    frontmatter, body = _split_frontmatter(content)

    # Pass 1: Translate tool names to sentinels / replacements
    for cli_tool, puppy_tool in _TOOL_MAP.items():
        body = re.sub(r'\b' + re.escape(cli_tool) + r'\b', puppy_tool, body)

    # Pass 2: Resolve interaction sentinels to human-readable guidance
    for sentinel, readable_text in _INTERACTION_SENTINELS.items():
        body = body.replace(sentinel, readable_text)

    # Translate CLI terminology
    for pattern, replacement in _TERM_REPLACEMENTS:
        body = re.sub(pattern, replacement, body, flags=re.IGNORECASE)

    # Reassemble
    if frontmatter:
        return f"---\n{frontmatter}\n---\n\n{body.lstrip()}"
    return body


def _enhance_frontmatter(content: str) -> str:
    """Add PuppyCLI adaptation metadata to YAML frontmatter."""
    frontmatter, body = _split_frontmatter(content)

    # Add adaptation fields if they don't exist
    adaptation_fields = [
        ("puppycli_adapted", "true"),
        ("puppycli_adapted_date", "auto"),
    ]

    if frontmatter:
        for key, value in adaptation_fields:
            if key not in frontmatter:
                frontmatter += f"\n{key}: {value}"
    else:
        frontmatter = "puppycli_adapted: true\npuppycli_adapted_date: auto"

    return f"---\n{frontmatter}\n---\n\n{body.lstrip()}"


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split content into (frontmatter_dict_text, body)."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2)
    return "", content


def get_adaptation_info(skill_dir: Path) -> dict[str, Any]:
    """Get comprehensive adaptation info for a skill.

    Returns a dict suitable for display in the frontend.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"exists": False}

    adapted = is_adapted(skill_dir)
    has_original = (skill_dir / "SKILL.md.orig").exists()
    analysis = analyze_skill(skill_dir)

    return {
        "exists": True,
        "is_adapted": adapted,
        "has_original_backup": has_original,
        "analysis": analysis,
    }
