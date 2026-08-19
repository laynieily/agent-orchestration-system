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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from src.api.schemas import (
    ApprovalDetail,
    ApprovalSummary,
    ResolveRequest,
    TaskCreateRequest,
    TaskStatusResponse,
    ChatRequest,
)
from src.api.state import get_state
from src.schemas.models import ApprovalLevel, EscalationEvent, new_id
from fastapi import WebSocket
from src.api.websocket_manager import manager

app = FastAPI(title="Agent Orchestration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _process_result(thread_id: str, result: dict) -> TaskStatusResponse:
    state = get_state()

    async def _broadcast(event_type: str, payload: dict):
        await manager.broadcast({
            "type": event_type,
            "payload": payload
        })

    if "__interrupt__" in result and result["__interrupt__"]:
        interrupt_obj = result["__interrupt__"][0]
        event_dict = interrupt_obj.value

        event = EscalationEvent(**event_dict)

        #store in approval queue
        approval_id = state.queue.submit(event)
        state.approval_to_thread[approval_id] = thread_id

        #record thread status
        state.thread_status[thread_id] = {
            "status": "paused",
            "final_output": None,
            "pending_approval_id": approval_id, 
        }

        return TaskStatusResponse(
            thread_id=thread_id,
            status="paused",
            final_output=None,
            pending_approval_id=approval_id,
        )
    # graph completed normally:
    final_status = result.get("status", "completed")
    final_output = result.get("final_output")

    state.thread_status[thread_id] = {
        "status": final_status,
        "final_output": final_output,
        "pending_approval_id": None,
    }

    return TaskStatusResponse(
        thread_id=thread_id,
        status=final_status,
        final_output=final_output,
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
    )


@app.post("/approvals/{approval_id}/resolve", response_model=TaskStatusResponse)
def resolve_approval(approval_id: str, body: ResolveRequest):
    state = get_state()
    event = state.queue.get(approval_id)
    if event is None:
        raise HTTPException(404, "approval not found")
    thread_id = state.approval_to_thread[approval_id]

    # Build resume payload based on approval level
    if event.level == ApprovalLevel.APPROVE_PLAN:
        resume_payload = {
            "approved": body.decision == "approved",
            "notes": body.notes,
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

    return _process_result(thread_id, result)