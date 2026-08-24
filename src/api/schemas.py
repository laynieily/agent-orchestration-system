"""
Pydantic request/response models for the API layer. These are separate
from src/schemas/models.py (the domain models) -- these describe what
goes over the wire.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TaskCreateRequest(BaseModel):
    request: str


class TaskStatusResponse(BaseModel):
    thread_id: str
    status: str
    final_output: Optional[str] = None
    writer_output: Optional[str] = None
    pending_approval_id: Optional[str] = None


class ApprovalSummary(BaseModel):
    id: str
    task_id: str
    level: str
    reason: str
    created_at: float


class ApprovalDetail(ApprovalSummary):
    context: dict
    resolution: Optional[str] = None
    resolution_notes: str = ""
    resolved_at: Optional[float] = None


class ResolveRequest(BaseModel):
    decision: str                   # "approved"/"rejected"/"take_over"/"abort" (plan) or "accept"/"take_over"/"abort" (subtask)
    notes: str = ""
    output: Optional[str] = None    # subtask take_over: the output to use
    edited_plan: Optional[dict] = None  # plan take_over: the edited ExecutionPlan

class ChatRequest(BaseModel):
    message: str

class TaskHistoryItem(TaskStatusResponse):
    request: str


class SubtaskProgress(BaseModel):
    id: str
    description: str
    assigned_specialist: str
    status: str  # "completed" | "current" | "pending"


class ApprovalProgress(BaseModel):
    original_request: str
    plan_confidence: Optional[float] = None
    plan_rationale: Optional[str] = None
    subtasks: list[SubtaskProgress] = []
    completed_count: int = 0
    total_count: int = 0


class MemoryEntry(BaseModel):
    task_id: str
    summary: str
    success: bool
    distance: float


class AskMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[AskMessage] = []


class AskResponse(BaseModel):
    answer: str