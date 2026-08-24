"""
Selects which LLM backend to use for a given role (planner/specialist/reviewer).
If an API key is present in .env, a real chat model is used; otherwise this
falls back to MockLLM so the whole system runs for free during development.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from src.llm.mock import MockLLM

load_dotenv()

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def using_real_model() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))


@lru_cache(maxsize=None)
def get_llm(role: str):
    """
    `role` is just a cache key / label (e.g. "planner", "specialist", "reviewer").
    All roles currently resolve to the same underlying model, but keeping it
    role-based means you can later route different roles to different models
    or temperatures without touching call sites.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        # claude-opus-5 (and the rest of the 4.6+/5 family) runs adaptive
        # thinking by default and rejects sampling params -- `temperature`
        # returns a 400 ("temperature is deprecated for this model").
        # max_tokens must cover thinking + the actual answer: the default of
        # 4096 was getting fully consumed by thinking on synthesis-heavy
        # subtasks (weighted comparison matrices, etc.), leaving zero tokens
        # for the visible text block and producing an empty specialist output.
        return ChatAnthropic(model=ANTHROPIC_MODEL, max_tokens=16000)

    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=OPENAI_MODEL, temperature=0)

    return MockLLM()