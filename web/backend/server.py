"""
FastAPI server — serves the frontend and exposes SSE streaming endpoint.
Run with: uvicorn web.backend.server:app --reload
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from web.backend.stream import stream_trading_analysis

app = FastAPI(title="Agentic Trading Dashboard")

# Resolve frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main dashboard page."""
    index_html = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=index_html.read_text(encoding="utf-8"))


@app.get("/api/analyze")
async def analyze():
    """SSE endpoint — streams agent events as they complete."""
    return StreamingResponse(
        stream_trading_analysis(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Mount static assets (CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
