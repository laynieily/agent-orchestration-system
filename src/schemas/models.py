from __future__ import annotations

import time 
import uuid 
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field 


# we need a way to generate IDs, which are unique. this will be for subtasks, tool calls, plans, and escalation events. 

def new_id(prefix: str) -> str:
    random_hex = uuid.uuid4().hex[:10]
    return f"{prefix}_{random_hex}"

# define complexity of the task (low, medium, high)
# define the specialist name
#  --can be done with ENUMS
class Complexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SpecialistName(str, Enum):
    RESEARCHER = "researcher"
    DATA_ANALYSIS = "data analyst"
    WRITER = "writer"
    CODE_EXECUTION = "code executioner"

#creating subtasks
class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sub"))
    description: str
    assigned_specialist: SpecialistName
    required_inputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list) #other subtask ids
    expected_output_format: str
    estimated_complexity: Complexity = Complexity.MEDIUM

#execution plan
class ExecutionPlan(BaseModel):
    task_id: str =Field(default_factory=lambda: new_id("task"))
    original_request: str
    subtasks: list[SubTask]
    confidence: float = Field(ge=0.0, le=1.0) #constrain it between 0 and 1
    rationale: str = ""

    def subtask_by_id(self, sub_id: str) -> Optional[SubTask]:
        return next((s for s in self.subtasks if s.id == sub_id), None)

    def ready_subtasks(self, completed_ids: set[str]) -> list[SubTask]:
        return [
            s for s in self.subtasks
            if s.id not in completed_ids
            and all(dep in completed_ids for dep in s.depends_on)
        ]

class ToolCallLog(BaseModel):
    id: str = Field(default_factory=lambda: new_id("call"))
    tool_name: str
    agent: str
    inputs: dict[str, Any]
    output: Any
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class SpecialistResult(BaseModel):
    subtask_id: str
    specialist: SpecialistName
    output: str 
    tool_calls: list[ToolCallLog] = Field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class ReviewResult(BaseModel):
    subtask_id: str
    approved: bool
    feedback: str = Field(default= "")
    quality_score: float = Field(ge=0.0, le=1.0)


class ApprovalLevel(str, Enum):
    NOTIFY = "notify"
    APPROVE_ACTION = "approve_action"
    APPROVE_PLAN = "approve_plan"
    TAKE_OVER = "take_over"


class EscalationEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("esc"))
    task_id: str
    reason: str
    level: ApprovalLevel 
    context: dict[str, Any] = Field(default_factory=dict)
    resolution: Optional[str] = None
    #   (values will be "approved" / "rejected" / "modified" / "auto")
    resolution_notes: str = Field(default= "")
    created_at: float = Field(default_factory=time.time)
    resolved_at: Optional[float] = Field(default =None)
    