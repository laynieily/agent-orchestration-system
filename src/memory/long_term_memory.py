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
        persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection("task_memory")
        
    def record_task(self, task_id: str, original_request: str, final_output: str,
                     tools_used: list[str], success: bool) -> None:
        
        summary = (
              f"Request: {original_request}\n"
              f"Outcome: {'succeeded' if success else 'failed'}\n"
              f"Tools used: {', '.join(tools_used)}\n"
              f"Result: {final_output[:500]}"
          )

        self.collection.add(
            documents=[summary],
            ids=[task_id],
            metadatas=[{"success": success, "tools_used": ",".join(tools_used)}],
        )

    def as_planning_context(self, request: str, n_results: int = 3) -> list[str]:
        results = self.query_similar(request, n_results=n_results)

        formatted = []
        for r in results:
            meta = r["metadata"]
            summary = r["summary"]
            succeeded = meta.get("success", False)
            outcome = "succeeded" if succeeded else "failed"

            formatted.append(f"[{outcome}] {summary}")

        return formatted
        

    def query_similar(self, request: str, n_results: int = 3) -> list[dict[str, Any]]:
        results = self.collection.query(query_texts=[request], n_results=n_results)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]]) [0]
        dists = results.get("distances", [[]])[0]

        return [
            {
                "summary": doc,
                "metadata": meta,
                "distance": dist,
    
            }
            for doc, meta, dist in zip(docs, metas, dists)
        ]