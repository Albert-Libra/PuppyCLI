"""Knowledge summarizer — extract terms and insights from conversations.

Uses the configured LLM to summarize key information from dialogues
and incrementally update the knowledge base.
"""
from __future__ import annotations


SUMMARY_PROMPT = """Analyze the following conversation snippet and extract:

1. **Key Terminology**: New technical terms, acronyms, or concepts discussed
2. **User Preferences**: Any preferences or requirements the user expressed
3. **Actionable Knowledge**: Facts, decisions, or insights worth remembering

Format your response as JSON:
{
  "terms": [{"term": "...", "definition": "..."}],
  "preferences": ["..."],
  "insights": [{"title": "...", "content": "..."}]
}

Respond ONLY with the JSON object, no other text.

Conversation:
{conversation}
"""


def build_summary_prompt(conversation: str) -> str:
    """Build the prompt for knowledge extraction."""
    # Truncate if too long
    if len(conversation) > 8000:
        conversation = conversation[:4000] + "\n...[truncated]...\n" + conversation[-4000:]
    return SUMMARY_PROMPT.format(conversation=conversation)


def parse_summary_response(response: str) -> dict:
    """Parse the LLM's JSON response into a structured dict."""
    import json
    import re

    # Try to extract JSON from response
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Find JSON block in markdown code fences
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try to find raw JSON
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"terms": [], "preferences": [], "insights": []}
