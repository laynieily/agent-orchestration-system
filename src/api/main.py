"""
FastAPI backend exposing task creation + human-in-the-loop approvals.

Flow:
  1. POST /tasks kicks off a graph run. If the graph pauses on an
     interrupt (low-confidence plan, or a subtask that exhausted
     retries), the pausing event is captured and pushed into the
     ApprovalQueue instead of being returned as an error.
  2. GET /approvals / GET /approvals/{id} let the review UI see what's
     waiting on a human.
  3. POST /approvals/{id}/resolve builds the right resume payload for
     the escalation type, resumes the graph with Command(resume=...),
     and (if THAT run pauses again) repeats step 1's capture logic.
"""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from src.api.schemas import (
    ApprovalDetail,
    ApprovalProgress,
    ApprovalSummary,
    AskRequest,
    AskResponse,
    MemoryEntry,
    ResolveRequest,
    SubtaskProgress,
    TaskCreateRequest,
    TaskHistoryItem,
    TaskStatusResponse,
    ChatRequest,
)
from src.api.state import get_state
from src.llm.provider import get_llm
from src.schemas.models import ApprovalLevel, EscalationEvent, SpecialistName, new_id
from fastapi import WebSocket
from src.api.websocket_manager import manager


def _extract_writer_output(result: dict) -> str | None:
    """Pull the writer specialist's own text out of the graph state, separate
    from the combined multi-specialist final_output."""
    writer_output = None
    for specialist_result in (result.get("completed") or {}).values():
        if specialist_result.specialist == SpecialistName.WRITER:
            writer_output = specialist_result.output
    return writer_output


def _extract_text(raw) -> str:
    """Same content-block handling as src.agents.specialist._extract_text --
    with adaptive thinking on, ChatAnthropic's `.content` is a list of blocks
    (thinking + text), not a plain string."""
    content = getattr(raw, "content", raw)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            else:
                text = getattr(block, "text", None)
                if text is not None:
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _approval_query_text(event: EscalationEvent) -> str:
    """The text to use for a memory-similarity search against this
    escalation -- the plan's original request, or the subtask's description."""
    if event.level == ApprovalLevel.APPROVE_PLAN:
        return (event.context.get("plan") or {}).get("original_request") or event.reason
    return (event.context.get("subtask") or {}).get("description") or event.reason

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Route handlers below are sync `def`s, which FastAPI runs in a worker
    # thread -- broadcast_threadsafe needs the loop to hop back to it.
    manager.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="Agent Orchestration API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Vite picks the next free port (5174, 5175, ...) whenever 5173 is
    # already taken by a leftover dev server, so a hardcoded origin list
    # silently breaks every request until someone notices. Match any
    # localhost/127.0.0.1 port instead -- this is a local dev server only.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _process_result(thread_id: str, result: dict) -> TaskStatusResponse:
    state = get_state()
    original_request = result.get("original_request", "")

    if "__interrupt__" in result and result["__interrupt__"]:
        interrupt_obj = result["__interrupt__"][0]
        event_dict = interrupt_obj.value
        event = EscalationEvent(**event_dict)

        approval_id = state.queue.submit(event)
        state.approval_to_thread[approval_id] = thread_id
        writer_output = _extract_writer_output(result)

        state.thread_status[thread_id] = {
            "status": "paused",
            "final_output": None,
            "writer_output": writer_output,
            "pending_approval_id": approval_id,
            "request": original_request,
        }

        manager.broadcast_threadsafe({
            "type": "task_update",
            "thread_id": thread_id,
            "status": "paused",
            "final_output": None,
            "writer_output": writer_output,
            "pending_approval_id": approval_id,
        })

        return TaskStatusResponse(
            thread_id=thread_id,
            status="paused",
            final_output=None,
            writer_output=writer_output,
            pending_approval_id=approval_id,
        )

    final_status = result.get("status", "completed")
    final_output = result.get("final_output")
    writer_output = _extract_writer_output(result)

    state.thread_status[thread_id] = {
        "status": final_status,
        "final_output": final_output,
        "writer_output": writer_output,
        "pending_approval_id": None,
        "request": original_request,
    }

    manager.broadcast_threadsafe({
        "type": "task_update",
        "thread_id": thread_id,
        "status": final_status,
        "final_output": final_output,
        "writer_output": writer_output,
        "pending_approval_id": None,
    })

    return TaskStatusResponse(
        thread_id=thread_id,
        status=final_status,
        final_output=final_output,
        writer_output=writer_output,
        pending_approval_id=None,
    )


# CHAT ENDPOINT

@app.post("/chat", response_model=TaskStatusResponse)
def chat(body: ChatRequest):
    state = get_state()
    thread_id = new_id("thread")

    result = state.graph.invoke(
        {"original_request": body.message},
        config = state.config_for(thread_id)
    )

    return _process_result(thread_id, result)

@app.get("/tasks", response_model=list[TaskHistoryItem])
def list_tasks():
    state = get_state()
    return [
        TaskHistoryItem(
            thread_id=tid,
            status=info["status"],
            final_output=info["final_output"],
            writer_output=info.get("writer_output"),
            pending_approval_id=info["pending_approval_id"],
            request=info.get("request", ""),
        )
        for tid, info in state.thread_status.items()
    ]

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except Exception:
        manager.disconnect(ws)

@app.post("/tasks", response_model=TaskStatusResponse)
def create_task(body: TaskCreateRequest):
    state = get_state()
    thread_id = new_id("thread")
    result = state.graph.invoke({"original_request": body.request}, config=state.config_for(thread_id))
    return _process_result(thread_id, result)



@app.get("/tasks/{thread_id}", response_model=TaskStatusResponse)
def get_task(thread_id: str):
    state = get_state()
    if thread_id not in state.thread_status:
        raise HTTPException(404, "task not found")

    ts = state.thread_status[thread_id]

    return TaskStatusResponse(
        thread_id=thread_id,
        status=ts["status"],
        final_output=ts["final_output"],
        writer_output=ts.get("writer_output"),
        pending_approval_id=ts["pending_approval_id"],
    )


@app.get("/approvals", response_model=list[ApprovalSummary])
def list_approvals():
    state = get_state()
    pending = state.queue.list_pending()

    return [
        ApprovalSummary(
            id=e.id,
            task_id=e.task_id,
            level=e.level,
            reason=e.reason,
            created_at=e.created_at,
        )
        for e in pending
    ]


@app.get("/approvals/history", response_model=list[ApprovalDetail])
def list_approval_history(resolution: str | None = None):
    state = get_state()
    resolved = state.queue.list_resolved(resolution)

    return [
        ApprovalDetail(
            id=e.id,
            task_id=e.task_id,
            level=e.level,
            reason=e.reason,
            context=e.context,
            created_at=e.created_at,
            resolution=e.resolution,
            resolution_notes=e.resolution_notes,
            resolved_at=e.resolved_at,
        )
        for e in resolved
    ]


@app.get("/approvals/{approval_id}", response_model=ApprovalDetail)
def get_approval(approval_id: str):
    state = get_state()
    event = state.queue.get(approval_id)

    if event is None:
        raise HTTPException(404, "approval not found")

    return ApprovalDetail(
        id=event.id,
        task_id=event.task_id,
        level=event.level,
        reason=event.reason,
        context=event.context,
        created_at=event.created_at,
        resolution=event.resolution,
        resolution_notes=event.resolution_notes,
        resolved_at=event.resolved_at,
    )


@app.get("/approvals/{approval_id}/progress", response_model=ApprovalProgress)
def get_approval_progress(approval_id: str):
    """Task context + execution progress: the plan and which subtasks are
    already done, in progress, or still pending as of this pause point."""
    state = get_state()
    event = state.queue.get(approval_id)
    if event is None:
        raise HTTPException(404, "approval not found")
    thread_id = state.approval_to_thread[approval_id]

    snapshot = state.graph.get_state(state.config_for(thread_id))
    values = snapshot.values or {}
    plan = values.get("plan")
    completed = values.get("completed") or {}
    current_subtask_id = values.get("current_subtask_id")

    if plan is None:
        original_request = state.thread_status.get(thread_id, {}).get("request", "")
        return ApprovalProgress(original_request=original_request)

    subtasks = []
    for sub in plan.subtasks:
        if sub.id in completed:
            status = "completed"
        elif sub.id == current_subtask_id:
            status = "current"
        else:
            status = "pending"
        subtasks.append(SubtaskProgress(
            id=sub.id,
            description=sub.description,
            assigned_specialist=sub.assigned_specialist.value,
            status=status,
        ))

    return ApprovalProgress(
        original_request=plan.original_request,
        plan_confidence=plan.confidence,
        plan_rationale=plan.rationale,
        subtasks=subtasks,
        completed_count=len(completed),
        total_count=len(plan.subtasks),
    )


@app.get("/approvals/{approval_id}/memories", response_model=list[MemoryEntry])
def get_approval_memories(approval_id: str, n_results: int = 3):
    """Relevant past decisions: prior completed tasks whose request/subtask
    text is semantically similar to this one, pulled from long-term memory."""
    state = get_state()
    event = state.queue.get(approval_id)
    if event is None:
        raise HTTPException(404, "approval not found")

    query = _approval_query_text(event)
    results = state.long_term_memory.query_similar(query, n_results=n_results)

    return [
        MemoryEntry(
            task_id=r["id"],
            summary=r["summary"],
            success=bool(r["metadata"].get("success", False)),
            distance=r["distance"],
        )
        for r in results
    ]


@app.post("/approvals/{approval_id}/ask", response_model=AskResponse)
def ask_about_approval(approval_id: str, body: AskRequest):
    """Let the reviewer ask clarifying questions about a pending decision
    before deciding. This is a side-channel consultation only -- it reads
    the same context the review UI shows but never touches the paused
    graph/thread, so it can't accidentally advance or corrupt it."""
    state = get_state()
    event = state.queue.get(approval_id)
    if event is None:
        raise HTTPException(404, "approval not found")

    query = _approval_query_text(event)
    memories = state.long_term_memory.query_similar(query, n_results=3)
    memory_text = "\n".join(
        f"- [{'succeeded' if m['metadata'].get('success') else 'failed'}] {m['summary']}"
        for m in memories
    ) or "(none found)"

    history_text = "\n".join(f"{m.role}: {m.content}" for m in body.history)

    prompt = (
        "You are helping a human reviewer decide on a paused AI agent task. "
        "Answer their question using ONLY the context below -- if you don't "
        "know something from this context, say so rather than guessing.\n\n"
        f"Decision point: {event.reason}\n\n"
        f"Context:\n{json.dumps(event.context, indent=2, default=str)}\n\n"
        f"Relevant past decisions:\n{memory_text}\n\n"
        + (f"Conversation so far:\n{history_text}\n\n" if history_text else "")
        + f"Reviewer's question:\n{body.question}"
    )

    llm = get_llm("reviewer")
    raw = llm.invoke(prompt)
    answer = _extract_text(raw)

    return AskResponse(answer=answer)


@app.post("/approvals/{approval_id}/resolve", response_model=TaskStatusResponse)
def resolve_approval(approval_id: str, body: ResolveRequest):
    state = get_state()
    event = state.queue.get(approval_id)
    if event is None:
        raise HTTPException(404, "approval not found")
    if event.resolution is not None:
        raise HTTPException(409, "approval already resolved")
    thread_id = state.approval_to_thread[approval_id]

    if not state.try_acquire_thread(thread_id):
        raise HTTPException(409, "this task is already processing a previous request")

    try:
        # Build resume payload based on approval level
        if event.level == ApprovalLevel.APPROVE_PLAN:
            if body.decision == "take_over" and not body.edited_plan:
                raise HTTPException(400, "edited_plan is required when taking over a plan")

            resume_payload = {
                "action": body.decision,
                "notes": body.notes,
                "edited_plan": body.edited_plan,
            }

        elif event.level == ApprovalLevel.APPROVE_ACTION:
            resume_payload = {
                "action": body.decision,
                "notes": body.notes,
                "output": body.output or "",
            }

        else:
            raise HTTPException(400, f"Unknown approval level {event.level}")

        # Bookkeeping
        state.queue.resolve(
            approval_id,
            resolution=body.decision,
            notes=body.notes,
        )

        # Resume graph
        result = state.graph.invoke(
            Command(resume=resume_payload),
            config=state.config_for(thread_id)
        )
    finally:
        state.release_thread(thread_id)

    return _process_result(thread_id, result)