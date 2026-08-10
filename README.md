# Agent Orchestration System

A multi-agent orchestration platform: a Supervisor agent decomposes complex
tasks, delegates to specialized tool-using agents, a Reviewer validates
output, and low-confidence or failed steps escalate to a human. Built for
Project 15 (Agent Orchestration System with Tool Use, Memory, and
Human-in-the-Loop).

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Agent hierarchy, task decomposition, tool registry, LangGraph state machine | Completed |
| 2 | Short-term (Redis) + long-term (ChromaDB) memory | Not started |
| 3 | Human-in-the-loop approval queue + review UI | Not started |
| 4 | OpenTelemetry tracing + trace explorer UI | Not started |
| 5 | Docker Compose integration + e2e demo | Not started |
| 6 | Portfolio polish | Not started |

## Prerequisites

- Python 3.11+
- git
- Docker Desktop (only needed from Phase 5 onward)
- Optional: OpenAI and/or Anthropic API key — not required for Phase 1,
  see "Mock LLM" below

## Setup — Windows (PowerShell)

```powershell  hhhhh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Setup — macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Mock LLM

No API keys are required to build or test this project. `src/llm/provider.py`
returns a real `ChatOpenAI`/`ChatAnthropic` if a key is present in `.env`,
otherwise falls back to a deterministic `MockLLM`. This means the graph,
retries, and escalation logic can be fully built and tested for free —
add real keys later with no code changes.

## Running

```powershell
pytest -q
python -m scripts.run_demo
```