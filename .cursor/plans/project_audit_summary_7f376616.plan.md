---
name: Project Audit Summary
overview: Deliver a concise description of what the project does and identify the most important bugs discovered during read-only review.
todos:
  - id: summarize-purpose
    content: Explain core runtime flow and outputs concisely
    status: pending
  - id: report-bugs
    content: List confirmed likely bugs ordered by severity with file references
    status: pending
  - id: todo-1775642903442-y8cwimxo2
    content: ""
    status: pending
isProject: false
---

# Project Understanding And Bug Review

## What The Project Mainly Does

- The app is a `LangGraph`-based stock trading assistant for NSE symbols.
- `main.py` reads a ticker, pulls OHLCV data with `yfinance` via `fetch_data()`, then runs a 2-node graph from `agent/trading_agent.py`.
- Graph flow: `prepare_data` creates a text summary from recent candles, then `analyze` sends that summary to an LLM (Groq-compatible OpenAI API) and returns structured output (`BUY`/`SELL`, confidence, reasoning, entry price, risk notes).
- It also writes a local summary file under `Summary/`.
- `agent/nodes.py` contains a fundamentals-analysis path using `scrapper.py`, but this path is not currently wired into the active graph.

## Highest-Priority Bugs Found

- `agent/trading_agent.py`: `os.environ["GROQ_API_KEY"]` can raise `KeyError` when unset before your custom error handling runs.
- `main.py` + `data_loader.py`: calling `fetch_data(..., period="max")` while defaulting to `interval="5m"` is usually unsupported by Yahoo intraday history constraints, often causing empty results.
- `agent/nodes.py`: prompt path expects `fundamentals_system_prompt.md` while file is `fundamental_system_prompt.md` (filename mismatch).
- `agent/trading_agent.py`: writes to hard-coded `Summary` path without ensuring directory exists, causing `FileNotFoundError` on clean setups.
- `agent/schemas.py` vs `agent/trading_agent.py`: `AgentState` declares `fundamentals`, but initial state in `run_trading_agent()` omits it.
- `scrapper.py`: uses BeautifulSoup with `"lxml"` parser but dependency is not clearly declared in project dependencies.

## Suggested Next Step

- If you want, I can implement a small hardening patch set to fix these issues in one pass (env handling, safe data window defaults, prompt filename alignment, summary dir creation, state schema consistency, and parser dependency cleanup).

