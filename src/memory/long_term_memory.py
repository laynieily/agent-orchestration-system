"""
Long-term semantic memory: after a task completes, extract and store a
summary of what was asked and what happened, embedded via ChromaDB. Future
tasks query this to inform planning -- this is what lets the system "get
smarter" across tasks instead of starting fresh every time.
"""
from __future__ import annotations

import os
from typing import Any

import chromadb


class LongTermMemoryStore:
    def __init__(self, persist_dir: str = None) -> None:
        # TODO: persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        # self.client = chromadb.PersistentClient(path=persist_dir)
        # self.collection = self.client.get_or_create_collection("task_memory")
        # -- get_or_create means this is safe to call every time your app
        # starts up; it won't wipe existing memories.
        pass

    def record_task(self, task_id: str, original_request: str, final_output: str,
                     tools_used: list[str], success: bool) -> None:
        # TODO: build one text string that captures what's worth
        # remembering -- this is literally what gets embedded and searched
        # over later, so make it descriptive:
        #   summary = (
        #       f"Request: {original_request}\n"
        #       f"Outcome: {'succeeded' if success else 'failed'}\n"
        #       f"Tools used: {', '.join(tools_used)}\n"
        #       f"Result: {final_output[:500]}"
        #   )
        # Then: self.collection.add(
        #     documents=[summary],
        #     ids=[task_id],
        #     metadatas=[{"success": success, "tools_used": ",".join(tools_used)}],
        # )
        # IMPORTANT: Chroma metadata values must be str/int/float/bool --
        # no lists or dicts directly. That's why tools_used gets joined
        # into a comma-separated string for the metadata (the raw list is
        # fine inside the `summary` text itself, just not as metadata).
        pass

    def query_similar(self, request: str, n_results: int = 3) -> list[dict[str, Any]]:
        # TODO: results = self.collection.query(query_texts=[request], n_results=n_results)
        # Chroma's query() returns parallel lists nested one level deep
        # (it supports batch queries) -- since you're only sending one
        # query_text, everything you want is at index [0]:
        #   results["documents"][0], results["metadatas"][0], results["distances"][0]
        # zip those three together into a list of dicts, e.g.
        #   [{"summary": doc, "metadata": meta, "distance": dist}, ...]
        # and return it. Lower distance = more similar to the query.
        #
        # EDGE CASE: if the collection is empty (first run ever, nothing
        # stored yet), Chroma's query() still returns a valid response
        # with empty lists rather than erroring -- no special-casing
        # needed, your zip() will just produce an empty list naturally.
        pass