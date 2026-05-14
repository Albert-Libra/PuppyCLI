"""FastAPI application entry point for PuppyCLI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from puppycli.server.routes import router as api_router
from puppycli.server.websocket import router as ws_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="PuppyCLI",
        description="A local AI agent tool with browser-based GUI",
        version="0.1.0",
    )

    # CORS - allow all origins for local use
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router)
    app.include_router(ws_router)

    # Mount API docs (built HTML) — use /help to avoid conflict with FastAPI /docs
    docs_dir = Path(__file__).parent / "static" / "docs"
    if docs_dir.exists() and list(docs_dir.iterdir()):
        from starlette.responses import RedirectResponse

        @app.get("/help", include_in_schema=False)
        async def help_redirect():
            return RedirectResponse(url="/help/", status_code=302)

        app.mount("/help/", StaticFiles(directory=str(docs_dir), html=True), name="help_docs")
    else:
        @app.get("/help", include_in_schema=False)
        async def help_unavailable():
            from starlette.responses import HTMLResponse
            return HTMLResponse(
                "<html><body style='font-family:sans-serif;padding:2em'>"
                "<h2>Documentation not built</h2>"
                "<p>Run <code>python scripts/build_docs.py</code> from the project root.</p>"
                "</body></html>"
            )

    # Static files (SPA frontend) — must be last
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
