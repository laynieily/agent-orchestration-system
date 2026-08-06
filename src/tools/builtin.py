"""
Built-in tools for the Phase 1 tool registry. Real implementations where
it's safe to do so without credentials (web_search needs no API key,
db_query runs against a local seeded store) -- not pure mocks.
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, Optional

import requests
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup

from src.tools.registry import ToolRegistry, ToolSpec

# All file/db operations are sandboxed under this directory.
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SANDBOX_DIR = DATA_DIR / "workspace"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(relative_path: str) -> Path:
    target = (SANDBOX_DIR /relative_path).resolve()
    sandbox_root = SANDBOX_DIR.resolve()

    #make sure the target is in the sandbox
    if target == sandbox_root or sandbox_root in target.parents:
        return target

    raise ValueError(f"Unsafe path escape attempt: {relative_path}")


# web_search

class WebSearchInput(BaseModel):
    query: str
    max_results: int = Field(default=5, le=10)


def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    try: 
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q":query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        for body in soup.select(".result__body"):
            title_el = body.select_one(".result__title")
            snippet_el = body.select_one(".result__snippet")
            link_el = body.select_one("a.result__a")

            if not (title_el and snippet_el and link_el):
                continue

            results.append({
                "title": title_el.get_text(strip=True),
                "snippet": snippet_el.get_text(strip=True),
                "url": link_el.get("href", ""),
            })

            if results:
                return results
    except Exception:
        pass

    # offline fallback
    return [{
        "title": "Search unavailable",
        "snippet": "Network search could not be performed.",
        "url": "",
    }]


# file_read / file_write

class FileReadInput(BaseModel):
    path: str


class FileWriteInput(BaseModel):
    path: str
    content: str
    append: bool = False


def file_read(path: str) -> str:
    target = _safe_path(path) 
    if not target.exists(): 
        raise FileNotFoundError(f"File not found: {path}")
    return target.read_text()


def file_write(path: str, content: str, append: bool = False) -> str:
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True) 

    mode = "a" if append else "w"
    with open(target, mode, encoding="utf-8") as f:
        f.write(content)

    return str(target.relative_to(SANDBOX_DIR))


# code_execution

class CodeExecutionInput(BaseModel):
    code: str
    timeout_s: int = Field(default=5, le=15)


def code_execution(code: str, timeout_s: int = 5) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(SANDBOX_DIR),
        )
        return {
            "stdout": proc.stdout[:5000], 
            "stderr": proc.stderr[:5000],
            "returncode": proc.returncode,
            } 
    except subprocess.TimeoutExpired:
        return{
            "stdout": "",
            "stderr": f"Execution tiem out after {timeout_s} seconds.",
            "returncode": -1,
        }


# db_query

class DbQueryInput(BaseModel):
    query: str

_demo_conn: Optional[sqlite3.Connection] = None


def _get_demo_conn() -> sqlite3.Connection:
    global _demo_conn
    if _demo_conn is not None:
        return _demo_conn

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            status TEXT,
            created_at REAL
        );

        INSERT INTO tasks (title, status, created_at) VALUES
            ('Write documentation', 'complete', strftime('%s','now')),
            ('Implement tool registry', 'in_progress', strftime('%s','now')),
            ('Research agentic AI', 'complete', strftime('%s','now'));
    """)

    _demo_conn = conn
    return conn


def db_query(query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q.startswith("select"):
        raise ValueError("db_query only supports SELECT statements.")
    
    conn = _get_demo_conn()
    rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


# api_call

class ApiCallInput(BaseModel):
    url: str
    method: Literal["GET", "POST"] = "GET"
    json_body: Optional[dict[str, Any]] = None
    timeout_s: int = Field(default=8, le=20)


def api_call(url: str, method: str = "GET", json_body: Optional[dict] = None,
             timeout_s: int = 8) -> dict[str, Any]:
    try:
        resp = requests.request(method, url, json=json_body, timeout=timeout_s)

        content_type = resp.headers.get("content-type", "")
        body = ""

        if "application/json" in content_type:
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:2000]
        else:
            body = resp.text[:2000]

        return {
            "status_code": resp.status_code,
            "body": body,
        }

    except Exception as exc:
        return {
            "status_code": -1,
            "body": f"Request failed: {exc}",
        }



# registry wiring

def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(ToolSpec(
        name="web_search",
        description="DuckDuckGo HTML search scraper",
        func=web_search,
        input_schema=WebSearchInput,
        allowed_agents=["researcher"],
        rate_limit_per_minute=15,
    ))

    registry.register(ToolSpec(
        name="file_read",
        description="Read a file from sandbox",
        func=file_read,
        input_schema=FileReadInput,
        allowed_agents=["*"],
        rate_limit_per_minute=60,
    ))

    registry.register(ToolSpec(
        name="file_write",
        description="Write a file to sandbox",
        func=file_write,
        input_schema=FileWriteInput,
        allowed_agents=["*"],
        rate_limit_per_minute=60,
    ))

    registry.register(ToolSpec(
        name="code_execution",
        description="Execute Python code in sandbox",
        func=code_execution,
        input_schema=CodeExecutionInput,
        allowed_agents=["coder", "data_analysis"],
        rate_limit_per_minute=20,
    ))

    registry.register(ToolSpec(
        name="db_query",
        description="Query in-memory SQLite demo DB",
        func=db_query,
        input_schema=DbQueryInput,
        allowed_agents=["data_analysis"],
        rate_limit_per_minute=40,
    ))

    registry.register(ToolSpec(
        name="api_call",
        description="Simple HTTP GET/POST wrapper",
        func=api_call,
        input_schema=ApiCallInput,
        allowed_agents=["research", "data_analysis"],
        rate_limit_per_minute=20,
    ))

    return registry