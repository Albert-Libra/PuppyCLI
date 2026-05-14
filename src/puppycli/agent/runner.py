"""Agent runner wrapping openai-agents-python SDK."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING

from openai import AsyncOpenAI
from agents import Agent, Runner, set_default_openai_client
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

from puppycli.agent.tools import create_tools

if TYPE_CHECKING:
    from puppycli.config import Config


BASE_SYSTEM_PROMPT = """You are PuppyCLI, a browser-based AI assistant.
The user interacts with you through a web chat interface with full Markdown rendering.
You CAN display images — just output the Markdown image syntax and it will render.

## Image display (CRITICAL — read this first)
When asked to show an image, do NOT say you can't. Do NOT suggest opening file explorer.
Output exactly this Markdown format and the image WILL appear:
  ![description](/api/file?path=<absolute_path>)
Example: ![logo](/api/file?path=C:/path/to/image.png)
Formats: png, jpg, jpeg, gif, webp, svg, bmp.

## Your tools
- run_powershell — execute PowerShell commands on this Windows machine
- search_knowledge — search the user's personal knowledge base
- process_pdf_file — extract text from PDFs, saved to knowledge base
- web_search — search the internet via DuckDuckGo (free, no key needed)
- web_fetch — extract readable text from any URL

## Rules
- When the user asks a question, the knowledge base may contain relevant context
  automatically injected below. ALWAYS read it carefully and prioritize it over
  your general training knowledge. Cite knowledge base entries when you use them.
- You are a web app, NOT a terminal. Never say "CLI", "terminal", "command line".
- Never tell the user to manually open files, explorer, or run commands.
- Use your tools to do things for the user.
- For images: ALWAYS use the Markdown format above. It works. Just do it.

## Academic rigor
- Treat claims in papers as "what the authors assert", not established truth.
  Distinguish evidence from author interpretation. Note limitations explicitly.
- Load information progressively: metadata/abstract first, then conclusions,
  only then full text. Don't dump everything at once.
- When comparing studies, highlight methodological differences, sample sizes,
  effect sizes, and conflicts of interest — not just conclusions.
- Prefer citing specific findings over vague appeals to "the literature".
- Use proper academic English but stay concise. No bloated hedge phrases
  like "It is worth noting that..." or "Interestingly...".
- For writing tasks: match the target venue's conventions. Ask about
  journal, audience, and word limit if not specified.

## Style
- Be concise. Get straight to the point. No fluff, no filler, no unnecessary apologies.
- Use Markdown and LaTeX ($$...$$) for formatting."""


def _build_system_prompt(project_dir: Path | None = None) -> str:
    """Build the full system prompt including available skills."""
    from puppycli.skill.loader import build_skills_prompt
    skills_section = build_skills_prompt(project_dir)
    return BASE_SYSTEM_PROMPT + skills_section


def _build_knowledge_context(user_message: str) -> str:
    """Search knowledge base and format relevant context."""
    from puppycli.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    return store.search_and_format(user_message, top_k=3)


class AgentRunner:
    """Wraps openai-agents-python Runner for PuppyCLI."""

    def __init__(self, config: Config | None = None, project_dir: Path | None = None):
        if config is None:
            from puppycli.config import Config as _Config

            config = _Config()
        self._config = config
        self._project_dir = project_dir

    def _setup_client(self) -> OpenAIChatCompletionsModel:
        """Configure the OpenAI client and return a Chat Completions model."""
        api_key = self._config.get("api_key", "")
        if not api_key:
            raise ValueError(
                "API key is not configured. "
                "Please set your API key in the Settings panel."
            )
        base_url = self._config.get("base_url", "https://api.deepseek.com")
        model_name = self._config.get("model", "deepseek-chat")
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        set_default_openai_client(client, use_for_tracing=False)
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    async def run_stream(
        self, user_message: str, history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Run the agent and stream response tokens.

        Args:
            user_message: The user's input message.
            history: Previous conversation messages as [{"role":..., "content":...}, ...].

        Yields:
            String tokens from the LLM response.
        """
        chat_model = self._setup_client()

        # Build instructions with skills + knowledge context
        instructions = _build_system_prompt(self._project_dir)
        knowledge_context = _build_knowledge_context(user_message)
        if knowledge_context:
            instructions += knowledge_context

        agent = Agent(
            name="PuppyCLI Assistant",
            instructions=instructions,
            tools=create_tools(),
            model=chat_model,
        )

        # Build input with conversation history
        agent_input: str | list[dict] = user_message
        if history:
            history_input = []
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history_input.append({"role": "user", "content": content})
                elif role == "assistant":
                    history_input.append({"role": "assistant", "content": content})
            history_input.append({"role": "user", "content": user_message})
            agent_input = history_input

        result = Runner.run_streamed(
            starting_agent=agent,
            input=agent_input,
        )

        async for event in result.stream_events():
            if event.type == "raw_response_event" and hasattr(event.data, "delta"):
                # Only yield text deltas, skip tool-call argument deltas
                data_type = getattr(event.data, "type", "")
                if data_type == "response.output_text.delta":
                    delta = event.data.delta
                    if isinstance(delta, str) and delta:
                        yield delta
