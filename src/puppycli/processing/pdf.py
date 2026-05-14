"""PDF processing via MinerU.

Supports two modes:
1. Free local mode (default): uses mineru-open-sdk, no API key needed
2. Cloud API mode: uses MinerU cloud API with token for higher limits
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def process_pdf_local(file_path: str | Path) -> dict:
    """Process PDF using local mineru-open-sdk (free, no API key).

    Args:
        file_path: Path to the PDF file.

    Returns:
        {"markdown": str, "filename": str, "pages": int, "mode": "local"}
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path.name}")

    try:
        from mineru import MinerU
    except ImportError:
        raise ImportError(
            "mineru-open-sdk is not installed. Run: pip install mineru-open-sdk"
        )

    client = MinerU()
    result = client.flash_extract(str(file_path))

    return {
        "markdown": result.markdown,
        "filename": file_path.name,
        "pages": getattr(result, "pages", 0),
        "mode": "local",
    }


def process_pdf_cloud(file_path: str | Path, token: str) -> dict:
    """Process PDF using MinerU cloud API.

    Args:
        file_path: Path to the PDF file.
        token: MinerU API token from https://mineru.net/apiManage

    Returns:
        {"markdown": str, "filename": str, "mode": "cloud"}
    """
    import time
    import json
    import requests

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path.name}")

    if file_path.stat().st_size > 200 * 1024 * 1024:
        raise ValueError("File too large (max 200MB for cloud API)")

    api_base = "https://mineru.net/api/v4"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Step 1: Get upload URL
    resp = requests.get(
        f"{api_base}/extract/upload-url",
        params={"fileName": file_path.name},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    upload_info = resp.json()
    upload_url = upload_info["data"]["uploadUrl"]
    file_id = upload_info["data"]["fileId"]

    # Step 2: Upload file
    with open(file_path, "rb") as f:
        resp = requests.put(upload_url, data=f, timeout=120)
        resp.raise_for_status()

    # Step 3: Create extraction task
    resp = requests.post(
        f"{api_base}/extract/task",
        json={"fileId": file_id, "fileName": file_path.name},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    task_data = resp.json()
    task_id = task_data["data"]["taskId"]

    # Step 4: Poll for completion
    for _ in range(60):
        time.sleep(3)
        resp = requests.get(
            f"{api_base}/extract/task/{task_id}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        status_data = resp.json()
        state = status_data["data"]["state"]

        if state == "done":
            result_url = status_data["data"]["result"]["fullUrl"]
            # Download markdown result
            md_resp = requests.get(result_url, timeout=60)
            md_resp.raise_for_status()
            return {
                "markdown": md_resp.text,
                "filename": file_path.name,
                "mode": "cloud",
            }
        elif state == "failed":
            raise RuntimeError(
                f"MinerU cloud processing failed: {status_data.get('data', {}).get('errMsg', 'unknown')}"
            )

    raise TimeoutError("PDF processing timed out (cloud API)")


def process_pdf(file_path: str | Path, token: str | None = None) -> dict:
    """Process a PDF file, auto-selecting local or cloud mode.

    Args:
        file_path: Path to PDF file.
        token: Optional MinerU API token. If provided, uses cloud API.

    Returns:
        {"markdown": str, "filename": str, "pages": int, "mode": str}
    """
    file_path = Path(file_path).expanduser().resolve()

    if token:
        return process_pdf_cloud(file_path, token)
    else:
        return process_pdf_local(file_path)


def save_to_knowledge(result: dict, tags: list[str] | None = None) -> str:
    """Save PDF processing result to knowledge base.

    Args:
        result: Dict from process_pdf().
        tags: Optional tags for the knowledge entry.

    Returns:
        The knowledge base entry ID.
    """
    from puppycli.knowledge.store import KnowledgeStore

    store = KnowledgeStore()
    title = f"PDF: {result['filename']}"
    content = result["markdown"]
    entry = store.add(
        title=title,
        content=content,
        tags=tags or ["pdf", "auto-extracted"],
        source=f"mineru-{result['mode']}",
    )
    return entry["id"]
