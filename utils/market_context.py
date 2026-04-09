"""
Global index cues + lightweight sentiment for index-focused trading agents.

Uses Finnhub (quotes + general market news) when FINNHUB_API_KEY is set.
Always tries Crypto Fear & Greed (alternative.me) as a no-key sentiment gauge.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()  # picks up FINNHUB_API_KEY (and others) from .env

FINNHUB_BASE = "https://finnhub.io/api/v1"
ALTERNATIVE_FNG_URL = "https://api.alternative.me/fng/?limit=1"

# Finnhub index symbols (verify against your subscription; free tier varies).
DEFAULT_INDICES: dict[str, str] = {
    "Dow Jones": "DJI",
    "S&P 500": "SPX",
    "Nasdaq": "IXIC",
    "FTSE 100": "UKX",
    "DAX": "DAX",
    "CAC 40": "CAC",
    "Nikkei 225": "NIK",
    "Hang Seng": "HSI",
    "Nifty 50": "NSEI",
    "Bank Nifty": "NIFTY_BANK",
    "Sensex": "BSESN",
}

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "LanggraphProject/1.0 (market-context; +https://github.com/)",
        "Accept": "application/json",
    }
)


@dataclass
class MarketContextConfig:
    output_dir: Path = Path("market_context_json")
    news_limit: int = 10
    request_timeout_s: float = 15.0


def _get_api_key() -> str | None:
    key = os.environ.get("FINNHUB_API_KEY", "").strip()
    return key or None


def finnhub_search_symbol(query: str, api_key: str, timeout: float) -> str | None:
    """Return first plausible index symbol from Finnhub search."""
    url = f"{FINNHUB_BASE}/search?q={quote(query)}&token={api_key}"
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None
    for item in (data.get("result") or [])[:8]:
        sym = item.get("symbol") or ""
        desc = (item.get("description") or "").lower()
        if not sym:
            continue
        if "index" in desc or sym in set(DEFAULT_INDICES.values()):
            return sym
    return None


def finnhub_quote(symbol: str, api_key: str, timeout: float) -> dict[str, Any]:
    url = f"{FINNHUB_BASE}/quote?symbol={quote(symbol)}&token={api_key}"
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"error": str(e), "symbol": symbol}
    except ValueError as e:
        return {"error": str(e), "symbol": symbol}

    price = data.get("c")
    if price is None or price == 0:
        return {"error": "No price data", "symbol": symbol, "raw": data}

    return {
        "symbol": symbol,
        "price": round(float(price), 4),
        "change": round(float(data.get("d") or 0), 4),
        "percent_change": round(float(data.get("dp") or 0), 4),
        "high": data.get("h"),
        "low": data.get("l"),
        "open": data.get("o"),
        "previous_close": data.get("pc"),
        "timestamp": data.get("t"),
        "error": None,
    }


def finnhub_general_news(api_key: str, limit: int, timeout: float) -> list[dict[str, Any]]:
    url = f"{FINNHUB_BASE}/news?category=general&token={api_key}"
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data[:limit]:
        out.append(
            {
                "datetime": item.get("datetime"),
                "headline": item.get("headline"),
                "source": item.get("source"),
                "summary": (item.get("summary") or "")[:500],
                "url": item.get("url"),
            }
        )
    return out


def fetch_fear_greed(timeout: float) -> dict[str, Any]:
    try:
        resp = SESSION.get(ALTERNATIVE_FNG_URL, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        row = (data.get("data") or [{}])[0]
        return {
            "value": row.get("value"),
            "classification": row.get("value_classification"),
            "timestamp": row.get("timestamp"),
            "error": None,
        }
    except (requests.RequestException, ValueError, IndexError, KeyError) as e:
        return {"error": str(e)}


def collect_index_snapshots(
    api_key: str | None,
    indices: dict[str, str] | None,
    timeout: float,
) -> list[dict[str, Any]]:
    mapping = indices or DEFAULT_INDICES
    rows: list[dict[str, Any]] = []
    if not api_key:
        for name, sym in mapping.items():
            rows.append(
                {
                    "name": name,
                    "symbol_requested": sym,
                    "symbol_used": sym,
                    "quote": None,
                    "error": "FINNHUB_API_KEY not set",
                }
            )
        return rows

    for name, default_symbol in mapping.items():
        used = default_symbol
        q = finnhub_quote(used, api_key, timeout)
        if q.get("error"):
            found = finnhub_search_symbol(name, api_key, timeout)
            if found and found != used:
                used = found
                q = finnhub_quote(used, api_key, timeout)
        rows.append(
            {
                "name": name,
                "symbol_requested": default_symbol,
                "symbol_used": used,
                "quote": q if not q.get("error") else None,
                "error": q.get("error"),
            }
        )
    return rows


def _breadth_summary(index_rows: list[dict[str, Any]]) -> str:
    up = down = nodata = 0
    for row in index_rows:
        q = row.get("quote")
        if not q:
            nodata += 1
            continue
        pct = q.get("percent_change")
        if pct is None:
            nodata += 1
            continue
        if pct >= 0:
            up += 1
        else:
            down += 1
    return f"indices_up={up}, indices_down={down}, indices_no_data={nodata}"


def _clean_headline(raw: str) -> str:
    """Strip trailing source attribution like ' - Reuters' from a headline."""
    for sep in (" - ", " | ", " — "):
        if sep in raw:
            raw = raw[:raw.rfind(sep)]
    return raw.strip()


def _build_llm_context(
    index_rows: list[dict[str, Any]],
    news: list[dict[str, Any]],
    fng: dict[str, Any],
    warnings: list[str],
) -> str:
    """
    Build a compact, token-efficient context string for the LLM.

    Rules applied to reduce noise:
    - Indices with no quote data are silently skipped (not listed).
    - News headlines are stripped of source suffixes and capped at 5.
    - Warnings block is omitted when empty.
    """
    lines: list[str] = ["### Global market context"]

    # ── Available index quotes only ──
    available = [r for r in index_rows if r.get("quote")]
    if available:
        lines.append("Indices (available):")
        for row in available:
            q = row["quote"]
            direction = "▲" if q["percent_change"] >= 0 else "▼"
            lines.append(
                f"  {row['name']}: {q['price']} "
                f"{direction}{abs(q['percent_change'])}%"
            )
    else:
        lines.append("Indices: no data available.")

    # ── Fear & Greed ──
    if not fng.get("error"):
        lines.append(f"Fear & Greed: {fng.get('value')}/100 — {fng.get('classification')}")

    # ── Top 5 clean headlines ──
    if news:
        lines.append("Headlines:")
        for n in news[:5]:
            hl = _clean_headline(n.get("headline") or "")
            if hl:
                lines.append(f"  - {hl}")
    
    # ── Warnings only if present ──
    if warnings:
        lines.append("Warnings: " + " | ".join(warnings))

    return "\n".join(lines)


def build_market_context_payload(
    *,
    indices: dict[str, str] | None = None,
    config: MarketContextConfig | None = None,
    persist: bool = True,
    symbol_for_filename: str = "market",
) -> dict[str, Any]:
    cfg = config or MarketContextConfig()
    api_key = _get_api_key()
    warnings: list[str] = []

    if not api_key:
        warnings.append(
            "FINNHUB_API_KEY is not set; index quotes and Finnhub news are skipped."
        )

    index_rows = collect_index_snapshots(api_key, indices, cfg.request_timeout_s)
    news: list[dict[str, Any]] = []
    if api_key:
        news = finnhub_general_news(api_key, cfg.news_limit, cfg.request_timeout_s)

    fng = fetch_fear_greed(cfg.request_timeout_s)
    if fng.get("error"):
        warnings.append(f"Fear & Greed fetch failed: {fng['error']}")

    derived = {
        "breadth": _breadth_summary(index_rows),
        "llm_context": _build_llm_context(index_rows, news, fng, warnings),
    }

    # Only keep indices that have real quote data, strip noise fields
    clean_indices = []
    for r in index_rows:
        q = r.get("quote")
        if not q:
            continue
        clean_indices.append({
            "name": r["name"],
            "price": q["price"],
            "change": q["change"],
            "percent_change": q["percent_change"],
        })

    # Headlines only — no URLs, no summaries
    clean_news = [
        _clean_headline(n.get("headline") or "")
        for n in news
        if n.get("headline")
    ]

    # Fear & Greed — just value + label
    clean_fng = {}
    if not fng.get("error"):
        clean_fng = {
            "value": fng.get("value"),
            "classification": fng.get("classification"),
        }

    payload: dict[str, Any] = {
        "fetched_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "indices": clean_indices,
        "headlines": clean_news,
        "fear_greed": clean_fng,
        "derived": derived,
    }
    if warnings:
        payload["warnings"] = warnings

    if persist:
        cfg.output_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in symbol_for_filename
        )[:80]
        out_path = cfg.output_dir / f"{safe}_market_context.json"
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        payload["json_output_path"] = str(out_path)

    return payload

if __name__ == "__main__":
    import pprint
    out = build_market_context_payload(symbol_for_filename="SBIN.NS")
    pprint.pprint(out)