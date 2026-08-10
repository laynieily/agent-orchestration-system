"""
Short-term working memory: a per-task, ephemeral store shared across agents
during a single task's execution -- the plan, completed subtask outputs,
intermediate results, and error logs. In production this would be backed
by Redis (fast, shared across processes/workers). For now it's a plain
in-memory dict with the same shape of interface -- swap the internals for
a real Redis client in Phase 5 without touching any calling code.
"""
from __future__ import annotations

from typing import Any


class WorkingMemoryStore:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def set(self, task_id: str, key: str, value: Any) -> None:
        self._store.setdefault(task_id, {})
        self._store[task_id][key] = value

    def get(self, task_id: str, key: str, default: Any = None) -> Any:
        # look up task_id, then key, falling back to `default` at
        # each level if either doesn't exist yet.
        return self._store.get(task_id, {}).get(key, default)

    def get_all(self, task_id: str) -> dict[str, Any]:
        return dict(self._store.get(task_id, {})) 

    def append_log(self, task_id: str, log_key: str, entry: Any) -> None:
        existing = self.get(task_id, log_key, default=[])
        #build a new list to avoid mutating shared defaults
        new_list = list(existing) + [entry]
        self.set(task_id, log_key, new_list)

    def clear(self, task_id: str) -> None:
        self._store.pop(task_id, None)