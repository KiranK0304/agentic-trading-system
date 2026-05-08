"""
FastAPI server — serves the frontend, exposes SSE streaming endpoint,
and runs background scheduled tasks for virtual paper trading.

Run with: uvicorn web.backend.server:app --reload
"""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler

from web.backend.portfolio import VirtualPortfolio
from web.backend.stream import stream_trading_analysis
from web.backend.tasks import update_price_task, run_agent_task

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-12s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("server")

# ── Global Portfolio Instance ──────────────────────────────────
portfolio = VirtualPortfolio(initial_capital=1_000_000.0, lot_size=25)

# ── Shared state for last agent run results ────────────────────
last_run_results: dict = {}

# ── Scheduler Setup ───────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the scheduler on startup, shut it down on shutdown."""

    from datetime import datetime as dt

    # ── Register jobs ──────────────────────────────────────────
    scheduler.add_job(
        update_price_task,
        trigger="interval",
        minutes=5,
        args=[portfolio],
        id="price_update_5m",
        name="Update price & unrealized P&L (every 5 min)",
        replace_existing=True,
        next_run_time=dt.now(),  # Run immediately on startup
    )

    scheduler.add_job(
        run_agent_task,
        trigger="interval",
        minutes=30,
        args=[portfolio, last_run_results],
        id="agent_run_30m",
        name="Run agent & execute virtual trade (every 30 min)",
        replace_existing=True,
        next_run_time=dt.now(),  # Run immediately on startup
    )

    scheduler.start()
    logger.info("🚀 Scheduler started — jobs registered:")
    for job in scheduler.get_jobs():
        logger.info(f"   • {job.name}  →  next run at {job.next_run_time}")

    yield  # ← App is running

    scheduler.shutdown(wait=False)
    logger.info("🛑 Scheduler shut down.")


# ── FastAPI App ────────────────────────────────────────────────
app = FastAPI(title="Agentic Trading Dashboard", lifespan=lifespan)

# Resolve frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Routes ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main dashboard page."""
    index_html = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=index_html.read_text(encoding="utf-8"))


@app.get("/api/analyze")
async def analyze():
    """SSE endpoint — streams agent events as they complete (read-only, no trade execution)."""
    return StreamingResponse(
        stream_trading_analysis(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/portfolio")
async def get_portfolio():
    """Returns the current virtual portfolio state and trade history."""
    state = portfolio.get_state()
    state["trade_history"] = portfolio.trade_history
    return JSONResponse(content=state)


@app.get("/api/schedule")
async def get_schedule():
    """Returns next run times for the scheduler jobs so the frontend can show countdowns."""
    jobs = {j.id: j for j in scheduler.get_jobs()}

    def _job_info(job_id, interval_minutes):
        job = jobs.get(job_id)
        if job and job.next_run_time:
            return {
                "next_run": job.next_run_time.isoformat(),
                "interval_minutes": interval_minutes,
            }
        return {"next_run": None, "interval_minutes": interval_minutes}

    return JSONResponse(content={
        "agent_run": _job_info("agent_run_30m", 30),
        "price_update": _job_info("price_update_5m", 5),
    })


@app.get("/api/last-run")
async def get_last_run():
    """Returns the full results from the most recent agent run."""
    return JSONResponse(content=last_run_results)


# Mount static assets (CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
