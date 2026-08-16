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
import time


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
            metadatas=[{"success": success, "tools_used": ",".join(tools_used), "access_count": 0, "created_at": time.time()}],
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
        

    def query_similar(self, request: str, n_results: int = 3, max_distance: float | None = None) -> list[dict[str, Any]]:
        results = self.collection.query(query_texts=[request], n_results=n_results)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]]) [0]
        dists = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]]) [0]

        #only treat relevant matches as "accessed"
        filtered = [
            (id_, doc, meta, dist)
            for id_, doc, meta, dist in zip(ids, docs, metas, dists)
            if max_distance is None or dist <= max_distance
        ]

        for id_, _doc, meta, _dist in filtered:
            count = meta.get("access_count", 0)
            meta["access_count"] = count + 1
            self.collection.update(ids=[id_], metadatas=[meta])

        return [
            {
                "id": id_,
                "summary": doc,
                "metadata": meta,
                "distance": dist,
    
            }
            for id_, doc, meta, dist in filtered
        ]

    def importance_score(self, task_id: str) -> float:
        result = self.collection.get(ids=[task_id])
        if not result.get("metadatas") or len(result["metadatas"]) == 0:
            return 0.0

        meta = result["metadatas"][0]

        #age in days 
        created_at = meta.get("created_at", time.time())
        age_days = (time.time() - created_at) / 86400 # seconds -> days

        #access count
        access_count = meta.get("access_count", 0)

        #importance formula: access_count decays over time
        return access_count / (1 + age_days)


    #remove old memory/expire them
    def expired_stale(self, max_age_days: float = 90, max_access_count: int = 0) -> int:
        #fetch everything
        result = self.collection.get()

        ids = result.get("ids", [])
        metas = result.get("metadatas", [])

        to_delete = []

        for id_, meta in zip(ids, metas):
            created_at = meta.get("created_at", time.time())
            age_days = (time.time() - created_at) / 86400

            #access count
            access_count = meta.get("access_count", 0)

            #stale = old and barely used
            if age_days > max_age_days and access_count <= max_access_count:
                to_delete.append(id_)

        if to_delete:
            self.collection.delete(ids=to_delete)
        return len(to_delete)

    #dashboard + delete endpoint

    def dashboard(self) -> list[dict[str, Any]]:
        result = self.collection.get()

        ids = result.get("ids", [])
        docs = result.get("documents", [])
        metas = result.get("metadatas", [])

        entries = []

        for id_, doc, meta in zip(ids, docs, metas):
            entries.append({
                "task_id": id_,
                "summary": doc,
                "metadata": meta,
                "importance": self.importance_score(id_)
            })

        #sort importance descending
        entries.sort(key=lambda x: x["importance"], reverse=True)

        return entries

    def delete_memory(self, task_id: str) -> None:
        self.collection.delete(ids=[task_id])