"""
Screener.in Excel export 

Use ``run_screener_export`` from another file; loads ``.env`` for
``SCREENER_USER`` / ``SCREENER_PASS`` when present.
"""

from __future__ import annotations

import os
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ── constants ─────────────────────────────────────────────────────────────
BASE_URL = "https://www.screener.in"
SEARCH_URL = f"{BASE_URL}/api/company/search/?q={{query}}&v=3&fts=1"
COMPANY_URL = f"{BASE_URL}/company/{{symbol}}/"
LOGIN_URL = f"{BASE_URL}/login/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Referer": BASE_URL,
}

__all__ = [
    "run_screener_export",
    "make_session",
    "login",
    "resolve_symbol",
    "download_export",
]


# ── session / auth ──────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def login(session: requests.Session, username: str, password: str) -> bool:
    resp = session.get(LOGIN_URL, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf_input:
        print("[ERROR] Could not find CSRF token on login page.")
        return False

    payload = {
        "csrfmiddlewaretoken": csrf_input["value"],
        "username": username,
        "password": password,
    }
    session.headers.update({"Referer": LOGIN_URL})
    resp = session.post(LOGIN_URL, data=payload, timeout=15)

    if resp.url == f"{BASE_URL}/" or "login" not in resp.url:
        print("[OK] Logged in successfully.")
        return True
    print("[ERROR] Login failed. Check your credentials.")
    return False


# ── lookup ──────────────────────────────────────────────────────────────────
def resolve_symbol(session: requests.Session, query: str) -> str | None:
    url = SEARCH_URL.format(query=requests.utils.quote(query))
    resp = session.get(url, timeout=15)
    resp.raise_for_status()

    results = resp.json()
    if not results:
        return None

    first = results[0]
    url_part = first.get("url", "")
    parts = [p for p in url_part.strip("/").split("/") if p]
    if len(parts) >= 2:
        symbol = parts[1]
        print(f"[INFO] Found company: {first.get('name', symbol)} → symbol: {symbol}")
        return symbol
    return None


# ── download ───────────────────────────────────────────────────────────────
def download_export(
    session: requests.Session,
    symbol: str,
    output_dir: str = ".",
    consolidated: bool = True,
) -> str | None:
    company_page_url = COMPANY_URL.format(symbol=symbol)
    if consolidated:
        company_page_url = f"{company_page_url}consolidated/"

    session.headers.update({"Referer": company_page_url})
    page_resp = session.get(company_page_url, timeout=30)
    if page_resp.status_code != 200:
        print(f"[ERROR] HTTP {page_resp.status_code} when loading company page.")
        return None

    soup = BeautifulSoup(page_resp.text, "lxml")
    export_btn = soup.find(attrs={"aria-label": "Export to Excel"})
    if not export_btn:
        print(
            "[ERROR] Could not find export button on company page.\n"
            "        This usually means you're not logged in.\n"
            "        Pass username/password or set SCREENER_USER / SCREENER_PASS."
        )
        return None

    export_path = export_btn.get("formaction", "").strip()
    if not export_path:
        print("[ERROR] Export endpoint not found on page.")
        return None

    export_url = f"{BASE_URL}{export_path}"
    export_form = export_btn.find_parent("form")
    payload: dict[str, str] = {}
    if export_form:
        for i in export_form.find_all("input"):
            name = i.get("name")
            if name:
                payload[name] = i.get("value", "")

    print(f"[INFO] Requesting export from: {export_url}")
    resp = session.post(export_url, data=payload, timeout=30, allow_redirects=True)

    if "register" in resp.url or "login" in resp.url:
        print(
            "[ERROR] Screener redirected to auth page.\n"
            "        Set SCREENER_USER / SCREENER_PASS in .env or pass username/password."
        )
        return None

    content_type = resp.headers.get("Content-Type", "").lower()
    content_disp_l = resp.headers.get("Content-Disposition", "").lower()
    is_excel = (
        "spreadsheet" in content_type
        or "excel" in content_type
        or "filename=" in content_disp_l
        or resp.content.startswith(b"PK")
    )
    if resp.status_code != 200 or not is_excel:
        print(f"[ERROR] Export request failed (HTTP {resp.status_code}).")
        return None

    content_disp = resp.headers.get("Content-Disposition", "")
    if "filename=" in content_disp:
        filename = content_disp.split("filename=")[-1].strip().strip('"').strip("'")
    else:
        filename = f"{symbol}.xlsx"

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "wb") as f:
        f.write(resp.content)

    size_kb = len(resp.content) / 1024
    print(f"[OK] Saved: {filepath}  ({size_kb:.1f} KB)")
    return filepath


def run_screener_export(
    query: str,
    output_dir: str = ".",
    *,
    login_flag: bool = False,
    no_login: bool = False,
    username: str | None = None,
    password: str | None = None,
    consolidated: bool = True,
    polite_delay_s: float = 1.0,
) -> str | None:
    """
    Download the Screener.in Excel export for ``query`` (company name or symbol).

    Calls ``load_dotenv()`` once so you can keep credentials in a ``.env`` file.

    Returns the path to the saved ``.xlsx`` file, or ``None`` on failure.

    Login is performed when ``not no_login`` and (``login_flag`` is True or both
    ``SCREENER_USER`` and ``SCREENER_PASS`` are set after loading dotenv).
    Pass ``username`` / ``password`` to override env vars.
    """
    load_dotenv()

    q = query.strip()
    if not q:
        print("[ERROR] query must be a non-empty string.")
        return None

    out = os.path.expanduser(output_dir)

    session = make_session()

    env_user = os.environ.get("SCREENER_USER", "").strip()
    env_pass = os.environ.get("SCREENER_PASS", "")
    has_env_creds = bool(env_user) and bool(env_pass)
    should_login = not no_login and (login_flag or has_env_creds)

    if should_login:
        u = (username if username is not None else env_user).strip()
        p = password if password is not None else env_pass
        if not u or not p:
            print(
                "[ERROR] Login required but username/password missing. "
                "Set SCREENER_USER and SCREENER_PASS (e.g. in .env) or pass username= and password=."
            )
            return None
        if not login(session, u, p):
            return None

    print(f"[INFO] Searching for: {q}")
    symbol = resolve_symbol(session, q)
    if not symbol:
        print(
            f"[WARN] Search returned no results. "
            f"Trying '{q.upper()}' directly as a symbol..."
        )
        symbol = q.upper()

    time.sleep(polite_delay_s)
    filepath = download_export(session, symbol, output_dir=out, consolidated=consolidated)

    if filepath:
        print(f"\n✅ Done! File saved to: {os.path.abspath(filepath)}")
    else:
        print("\n❌ Download failed. See errors above.")
    return filepath
