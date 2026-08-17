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
)
from src.api.state import get_state
from src.schemas.models import ApprovalLevel, EscalationEvent, new_id

app = FastAPI(title="Agent Orchestration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # adjust to your React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


def _process_result(thread_id: str, result: dict) -> TaskStatusResponse:
    """
    Shared handling for whatever app.invoke() returns -- either the graph
    paused on an interrupt, or it ran to completion (or further along).

    TODO:
      1. Check `"__interrupt__" in result`.
      2. If paused:
         - result["__interrupt__"] is a list of Interrupt objects; each
           has `.value`, which is the dict your node passed to
           interrupt(...) (i.e. event.model_dump()).
         - Rebuild it: EscalationEvent(**result["__interrupt__"][0].value)
         - approval_id = state.queue.submit(event)
         - state.approval_to_thread[approval_id] = thread_id
         - record thread_status as "paused", final_output None
         - return TaskStatusResponse(..., pending_approval_id=approval_id)
      3. Otherwise:
         - result is the final state dict -- pull "status" / "final_output"
           out of it and store + return those.
    """
    raise NotImplementedError


@app.post("/tasks", response_model=TaskStatusResponse)
def create_task(body: TaskCreateRequest):
    state = get_state()
    thread_id = new_id()
    # TODO: result = state.graph.invoke({"original_request": body.request}, config=state.config_for(thread_id))
    # TODO: return _process_result(thread_id, result)
    raise NotImplementedError


@app.get("/tasks/{thread_id}", response_model=TaskStatusResponse)
def get_task(thread_id: str):
    state = get_state()
    # TODO: look up state.thread_status[thread_id]; raise HTTPException(404, ...) if missing
    raise NotImplementedError


@app.get("/approvals", response_model=list[ApprovalSummary])
def list_approvals():
    state = get_state()
    # TODO: map state.queue.list_pending() -> list[ApprovalSummary]
    raise NotImplementedError


@app.get("/approvals/{approval_id}", response_model=ApprovalDetail)
def get_approval(approval_id: str):
    state = get_state()
    # TODO: state.queue.get(approval_id); 404 if None; map to ApprovalDetail
    raise NotImplementedError


@app.post("/approvals/{approval_id}/resolve", response_model=TaskStatusResponse)
def resolve_approval(approval_id: str, body: ResolveRequest):
    state = get_state()
    event = state.queue.get(approval_id)
    if event is None:
        raise HTTPException(404, "approval not found")
    thread_id = state.approval_to_thread[approval_id]

    # TODO: build resume_payload based on event.level:
    #   APPROVE_PLAN   -> {"approved": body.decision == "approved", "notes": body.notes}
    #   APPROVE_ACTION -> {"action": body.decision, "notes": body.notes, "output": body.output or ""}

    # TODO: state.queue.resolve(approval_id, resolution=body.decision, notes=body.notes)  # bookkeeping only

    # TODO: result = state.graph.invoke(Command(resume=resume_payload), config=state.config_for(thread_id))
    # TODO: return _process_result(thread_id, result)
    raise NotImplementedError