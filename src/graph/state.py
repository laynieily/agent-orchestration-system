"""
The LangGraph state: everything that flows between nodes in the pipeline.
"""
from __future__ import annotations

from typing import Optional, TypedDict

from src.schemas.models import EscalationEvent, ExecutionPlan, ReviewResult, SpecialistResult


class OrchestratorState(TypedDict, total=False):
    task_id: str
    original_request: str

    plan: Optional[ExecutionPlan]

    current_subtask_id: Optional[str]

    #holds the result produced by a specialist BEFORE review
    pending_result: Optional[SpecialistResult]
    # all complelted specialist results
    completed: dict[str, SpecialistResult]
    # all reviews results
    reviews: dict[str, ReviewResult]
    retries: dict[str, int]
    escalations: list[EscalationEvent]
    final_output: Optional[str]
    status: str