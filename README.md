# Multi-Agent Trading System

A production-style LangGraph trading workflow for Indian markets that combines:

- parallel Fundamental + Technical sub-agents,
- an Orchestrator that makes the trade decision,
- a Risk Manager that critiques that decision,
- and a final risk-aware re-evaluation pass.

## What This Project Does

Given recent 5-minute price candles and live market context, the system produces a structured intraday Futures-oriented decision:

- `BUY` or `SELL`
- confidence (1-100)
- reasoning
- entry price
- risk notes

The pipeline is schema-validated end to end using Pydantic models to keep LLM outputs structured and reliable.

## Graph Architecture

Important: this graph is not purely acyclic. It contains a deliberate review loop.

High-level flow:

1. `prepare` -> builds data summaries from OHLCV
2. `market_context` -> fetches macro context (indices, headlines, fear/greed)
3. Parallel branches:
   - `fundamental`
   - `technical`
4. `orchestrator` (pass 1)
5. `risk_manager`
6. `orchestrator` (pass 2, re-evaluation)
7. `END`

Cycle pattern:

- `orchestrator -> risk_manager -> orchestrator`

This loop is intentional and runs as a two-pass risk-aware decision process.

![LangGraph Architecture](trading_compiled_graph.png)

## Current Model Configuration

Configured in `agent/trading_agent.py`:

- Provider: `openrouter`
- Model (all agents): `openai/gpt-oss-120b:free`
- Structured output method: function calling

## Reliability Features

To reduce runtime failures from imperfect model outputs:

- Schema-level normalization/defaults in `agent/schemas.py`
- Node-level fallback handling in `agent/nodes.py`
- Tightened system prompts in `agent/prompts/` for strict enum/range/schema behavior
- User-friendly failure messaging in `main.py`

## Project Structure (Key Files)

- `main.py`: CLI entry point and top-level error handling
- `agent/trading_agent.py`: graph build, routing, execution
- `agent/nodes.py`: node implementations and node factories
- `agent/schemas.py`: state + output schemas
- `agent/llm_factory.py`: provider/model abstraction
- `agent/prompts/`: system prompts for all agent roles
- `web/backend/server.py`: FastAPI server that serves the frontend and SSE endpoint

## Setup

1. Create and activate your environment.

```bash
source .venv/bin/activate
```

2. Install dependencies.

```bash
uv sync
```

3. Configure environment variables in `.env`.

Minimum recommended keys:

- One LLM provider key (based on your selected provider in `agent/trading_agent.py` / `agent/llm_factory.py`), for example:
   - `OPENROUTER_API_KEY`
   - `GROQ_API_KEY`
   - `OPENAI_API_KEY`
   - `KIMI_API_KEY`
   - `NVIDIA_API_KEY`
- `FINNHUB_API_KEY` (for market context features)

## Run the CLI Pipeline

```bash
python main.py
```

The script fetches live + historical data concurrently, runs the full graph, and prints:

- Fundamental analysis
- Technical analysis
- Risk manager critique
- Final re-evaluated trade decision

## Run the Web App

This project currently serves frontend + backend from a single FastAPI process.

```bash
uvicorn web.backend.server:app --reload
```

Open:

- `http://127.0.0.1:8000`

No separate frontend dev server is required for the current setup.

## Notes

- The system analyzes Spot data but frames output for executable Futures decisions.
- If an LLM returns malformed structured output, the pipeline now degrades gracefully instead of crashing.
