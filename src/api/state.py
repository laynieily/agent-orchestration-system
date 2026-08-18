"""
Process-wide singletons for the API: the compiled LangGraph app, the
approval queue, and in-memory tracking of task status + which thread a
pending approval belongs to.

Because we're using MemorySaver, all of this only lives as long as the
API process is running -- restarting the server loses in-flight tasks.
That's fine for this project; a persistent checkpointer is a Phase 5 concern.
"""
from __future__ import annotations

from typing import Optional

from src.approval.queue import ApprovalQueue
from src.graph.build_graph import build_graph
from src.llm.provider import get_llm
from src.memory.long_term_memory import LongTermMemoryStore
from src.memory.working_memory import WorkingMemoryStore
from src.tools.builtin import build_default_registry


class AppState:
    def __init__(self) -> None:
        self.tools = build_default_registry()
        self.memory = WorkingMemoryStore()
        self.long_term_memory = LongTermMemoryStore(persist_dir=...)
        self.graph = build_graph(self.tools, self.memory, self.long_term_memory,
                                  get_llm("planner"), get_llm("specialist"), get_llm("reviewer"))
        self.queue = ApprovalQueue()
        self.thread_status: dict[str, dict] = {}       # thread_id -> {"status": ..., "final_output": ...}
        self.approval_to_thread: dict[str, str] = {}   # approval_id -> thread_id
        raise NotImplementedError

    def config_for(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}


state: Optional[AppState] = None


def get_state() -> AppState:
    global state
    if state is None:
        state = AppState()
    return state