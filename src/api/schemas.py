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


class ResolveRequest(BaseModel):
    decision: str                   # "approved"/"rejected" (plan) or "accept"/"take_over"/"abort" (subtask)
    notes: str = ""
    output: Optional[str] = None    # only used when decision == "take_over"

class ChatRequest(BaseModel):
    message: str