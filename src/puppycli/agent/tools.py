"""Built-in tools for PuppyCLI agent."""
import os
import re
import subprocess
from html.parser import HTMLParser
from urllib.parse import quote_plus

import requests
from agents import function_tool


# ---- Dangerous Command Detection ----

# Patterns that indicate file-modifying operations (case-insensitive)
_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # (regex_pattern, risk_description)
    # Deletion
    (r'\bRemove-Item\b',         "此命令会删除文件或目录"),
    (r'\bri\b',                  "此命令会删除文件或目录"),
    (r'\bdel\b',                 "此命令会删除文件"),
    (r'\brm\b',                  "此命令会删除文件"),
    (r'\brmdir\b',               "此命令会删除目录"),
    (r'\bClear-Content\b',       "此命令会清空文件内容"),
    (r'\bClear-RecycleBin\b',    "此命令会清空回收站"),
    # Write / Overwrite
    (r'\bSet-Content\b',         "此命令会写入或覆盖文件"),
    (r'\bOut-File\b',            "此命令会写入或覆盖文件"),
    (r'\bAdd-Content\b',         "此命令会修改文件内容"),
    (r'\bExport-',               "此命令会导出/写入文件"),
    # Move / Rename / Copy
    (r'\bMove-Item\b',           "此命令会移动文件"),
    (r'\bmi\b',                  "此命令会移动文件"),
    (r'\bRename-Item\b',         "此命令会重命名文件"),
    (r'\brni\b',                 "此命令会重命名文件"),
    (r'\bCopy-Item\b',           "此命令会复制文件"),
    (r'\bcopy\b',                "此命令会复制文件"),
    (r'\bcp\b',                  "此命令会复制文件"),
    # Creation
    (r'\bNew-Item\b',            "此命令会创建文件或目录"),
    (r'\bni\b',                  "此命令会创建文件或目录"),
    (r'\bmkdir\b',               "此命令会创建目录"),
    # Redirection (write to file)
    (r'>\s*\S',                  "此命令会将输出重定向写入文件"),
    # Permission / Attribute changes
    (r'\bSet-Acl\b',             "此命令会修改文件权限"),
    (r'\bSet-FileAttribute\b',   "此命令会修改文件属性"),
    (r'\battrib\b',              "此命令会修改文件属性"),
    (r'\bicacls\b',              "此命令会修改文件权限"),
    (r'\btakeown\b',             "此命令会修改文件所有权"),
    # Registry modification
    (r'\bSet-ItemProperty\b',    "此命令会修改注册表"),
    (r'\bNew-ItemProperty\b',    "此命令会修改注册表"),
    (r'\bRemove-ItemProperty\b', "此命令会删除注册表项"),
]


def is_dangerous_command(command: str) -> str | None:
    """Check if a PowerShell command is potentially file-modifying.

    Returns:
        A risk description string if dangerous, or None if safe.
    """
    for pattern, description in _DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return description
    return None


def _make_run_powershell(confirm_handler=None):
    """Create a run_powershell tool function, optionally with confirmation.

    Args:
        confirm_handler: Optional async callable with signature
            async def handler(command: str, reason: str) -> bool
            Returns True if user allowed, False to reject.
    """

    @function_tool
    async def run_powershell(command: str) -> str:
        """Execute a PowerShell command on the user's Windows machine.

        Use this tool when the user asks you to run a command, check system info,
        manage files, or perform any task that requires shell execution.

        Args:
            command: The PowerShell command to execute. Be specific and safe.

        Returns:
            The stdout output of the command, or stderr if it failed.
        """
        # Check for dangerous commands
        if confirm_handler is not None:
            risk = is_dangerous_command(command)
            if risk is not None:
                try:
                    allowed = await confirm_handler(command, risk)
                except Exception as exc:
                    import logging
                    logging.getLogger("puppycli").error(
                        "Confirm handler failed for command %r: %s", command, exc
                    )
                    return (
                        "COMMAND CONFIRMATION FAILED. "
                        f"The confirmation system encountered an error: {exc}. "
                        "This is NOT because the user rejected the command — "
                        "it is a system error. Please report this to the user and "
                        "ask if they would like you to try again or proceed differently."
                    )
                if not allowed:
                    return (
                        "COMMAND REJECTED BY USER. "
                        "The user chose not to allow this command to execute. "
                        "Do NOT attempt to run it again or try alternative commands "
                        "to achieve the same effect. Instead, explain to the user "
                        "what you wanted to do and ask if they would like to proceed "
                        "differently."
                    )

        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.getcwd(),
            )
            output = result.stdout.strip()
            if result.returncode != 0:
                err = result.stderr.strip()
                if err:
                    output = f"STDERR:\n{err}\n\nSTDOUT:\n{output}" if output else f"ERROR:\n{err}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 60 seconds"
        except Exception as e:
            return f"ERROR: {e}"

    return run_powershell


def create_tools(confirm_handler=None) -> list:
    """Create the list of built-in tools for the agent.

    Args:
        confirm_handler: Optional async callable for dangerous-command confirmation.
    """
    return [
        _make_run_powershell(confirm_handler),
        search_knowledge,
        process_pdf_file,
        web_search,
        web_fetch,
    ]


@function_tool
def search_knowledge(query: str) -> str:
    """Search the local knowledge base for relevant information.

    Use this tool when:
    - The user asks about something that might be in their knowledge base
    - You need context about the user's preferences or past decisions
    - You want to reference previously stored information

    Args:
        query: Search query string. Use keywords or natural language.

    Returns:
        Formatted search results from the knowledge base, or a message if nothing found.
    """
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    result = store.search_and_format(query, top_k=3)
    return result or "No relevant knowledge found. You can add to the knowledge base using /kb add commands."


@function_tool
def process_pdf_file(file_path: str) -> str:
    """Process a PDF file and extract its content as Markdown.

    Use this tool when the user asks you to read, analyze, or extract
    information from a PDF file.

    The extracted content is automatically saved to the knowledge base.

    Args:
        file_path: Absolute path to the PDF file on the user's system.

    Returns:
        A summary of the processing result, including the knowledge base entry ID
        and a preview of the extracted content.
    """
    from pathlib import Path

    from puppycli.config import Config
    from puppycli.processing.pdf import process_pdf, save_to_knowledge

    config = Config()
    token = config.get("mineru_token", "") or None

    try:
        result = process_pdf(file_path, token=token)
        kb_id = save_to_knowledge(result)

        preview = result["markdown"][:1500]
        if len(result["markdown"]) > 1500:
            preview += "\n\n...(truncated)"

        return (
            f"PDF processed successfully via MinerU ({result['mode']} mode).\n"
            f"Knowledge base entry ID: `{kb_id}`\n"
            f"File: {result['filename']}\n\n"
            f"**Preview:**\n{preview}"
        )
    except Exception as e:
        return f"PDF processing failed: {e}"


# ---- Web Tools ----


class _TextExtractor(HTMLParser):
    """Extract visible text from HTML, ignoring scripts and styles."""

    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self.text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self.text.append(t)


def _search_via_mcp(query: str) -> str | None:
    """Try searching via MCP server (same config as ScholarAIO). Returns None if unavailable."""
    import os

    mcp_url = os.environ.get("WEBSEARCH_MCP_URL") or "http://127.0.0.1:8765/mcp"
    tool_name = os.environ.get("WEBSEARCH_MCP_TOOL") or "search_bing"
    try:
        from puppycli.providers.mcp import call_mcp_tool, McpError

        result = call_mcp_tool(mcp_url, tool_name, {"query": query, "count": 8}, timeout=15)
        content = result.get("content", [])
        if not content:
            return None
        text = content[0].get("text", "") if isinstance(content, list) else str(content)
        if not text:
            return None
        return "## Web Search (MCP): " + query + "\n\n" + text
    except (McpError, Exception):
        return None


def _search_via_duckduckgo(query: str) -> str:
    """Search via DuckDuckGo Lite (free, no configuration needed)."""
    try:
        url = "https://lite.duckduckgo.com/lite/"
        resp = requests.post(
            url,
            data={"q": query, "kl": "us-en"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()

        results = []
        link_pattern = re.compile(
            r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?<span[^>]*class="link-text"[^>]*>([^<]*)</span>',
            re.DOTALL,
        )
        matches = link_pattern.findall(resp.text)
        for href, title, snippet in matches[:8]:
            title = title.strip()
            if not title:
                continue
            snippet = snippet.strip()
            results.append(f"- **{title}**\n  {snippet}\n  {href}")

        if not results:
            a_pattern = re.compile(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')
            snippets = re.findall(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', resp.text, re.DOTALL)
            links = a_pattern.findall(resp.text)
            for (href, title), snip in zip(links[:8], snippets[:8] if snippets else [""] * 8):
                title = title.strip()
                if not title:
                    continue
                snip_clean = re.sub(r"<.*?>", "", snip).strip()
                results.append(f"- **{title}**\n  {snip_clean}\n  {href}")

        if not results:
            return f"No results found for: {query}"
        return "## Web Search (DuckDuckGo): " + query + "\n\n" + "\n\n".join(results)

    except requests.RequestException as e:
        return f"Search failed (network error): {e}"
    except Exception as e:
        return f"Search failed: {e}"


@function_tool
def web_search(query: str) -> str:
    """Search the web. Uses local MCP server if available, otherwise DuckDuckGo.

    Use this tool when:
    - The user asks about current events, facts, or information not in your training data
    - You need up-to-date information from the internet
    - The user wants you to research a topic online

    Args:
        query: Search query string. Be specific for better results.

    Returns:
        Search results with titles, snippets, and URLs.
    """
    # Try MCP search server first
    result = _search_via_mcp(query)
    if result:
        return result

    # Fall back to DuckDuckGo
    return _search_via_duckduckgo(query)


@function_tool
def web_fetch(url: str) -> str:
    """Fetch and extract text content from a web page.

    Use this tool when:
    - You found a URL from web_search and want to read the full content
    - The user asks you to summarize a web article
    - You need to extract specific information from a webpage

    Args:
        url: Full URL of the webpage to fetch.

    Returns:
        Extracted text content (truncated to ~4000 chars).
    """
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PuppyCLI/0.1)"},
            timeout=15,
        )
        resp.raise_for_status()

        # Extract text from HTML
        parser = _TextExtractor()
        # Decode safely
        content = resp.content.decode(resp.encoding or "utf-8", errors="replace")
        parser.feed(content)
        text = " ".join(parser.text)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        if len(text) > 4000:
            text = text[:4000] + "\n\n...(truncated)"

        return text or "(No readable text found on this page)"

    except requests.RequestException as e:
        return f"Fetch failed (network error): {e}"
    except Exception as e:
        return f"Fetch failed: {e}"

