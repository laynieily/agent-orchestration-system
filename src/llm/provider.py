"""
Deterministic mock LLM used whenever no API key is configured. Implements
just enough of the LangChain chat-model surface (.invoke, and a
.with_structured_output(schema) returning something with the same
interface) that the rest of the codebase is provider-agnostic.
"""
from __future__ import annotations

import hashlib
from typing import Any, Type

from pydantic import BaseModel

from ..schemas.models import (
    Complexity,
    ExecutionPlan,
    ReviewResult,
    SpecialistName,
    SubTask,
)


class _StructuredMock:
    def __init__(self, schema: Type[BaseModel]):
        self.schema = schema

    def invoke(self, messages: Any) -> BaseModel:
        text = _flatten(messages)
        if self.schema is ExecutionPlan:
            return _mock_plan(text)
        if self.schema is ReviewResult:
            return _mock_review(text)
        try:
            return self.schema()
        except Exception:
            return self.schema.model_construct()


class MockLLM:
    def with_structured_output(self, schema: Type[BaseModel]) -> _StructuredMock:
        return _StructuredMock(schema)

    def invoke(self, messages: Any) -> str:
        text = _flatten(messages)
        digest = hashlib.sha256(text.encode()).hexdigest()[:8]
        return f"[mock-llm:{digest}] Response synthesized from: {text[:200]}"


def _flatten(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    if isinstance(messages, list):
        parts = []
        for m in messages:
            content = getattr(m, "content", None)
            if content is None and isinstance(m, tuple):
                content = m[-1]
            parts.append(str(content if content is not None else m))
        return "\n".join(parts)
    return str(messages)


def _mock_plan(prompt_text: str) -> ExecutionPlan:
    marker = "Request:\n"
    request_text = prompt_text.split(marker, 1)[1].strip() if marker in prompt_text else prompt_text.strip()

    research = SubTask(
        description=f"Gather background information for: {request_text[:150]}",
        assigned_specialist=SpecialistName.research,
        required_inputs=["original request"],
        expected_output_format="A short list of findings with sources.",
        estimated_complexity=Complexity.medium,
    )
    analysis = SubTask(
        description="Analyze the research findings and extract key insights.",
        assigned_specialist=SpecialistName.data_analysis,
        required_inputs=[research.id],
        depends_on=[research.id],
        expected_output_format="A few bullet-point insights.",
        estimated_complexity=Complexity.medium,
    )
    writing = SubTask(
        description="Write a final summary combining the research and analysis.",
        assigned_specialist=SpecialistName.writing,
        required_inputs=[research.id, analysis.id],
        depends_on=[research.id, analysis.id],
        expected_output_format="A polished short-form written summary.",
        estimated_complexity=Complexity.low,
    )
    return ExecutionPlan(
        original_request=request_text,
        subtasks=[research, analysis, writing],
        confidence=0.75,
        rationale="[mock-llm] heuristic research -> analyze -> write decomposition",
    )


def _mock_review(review_text: str) -> ReviewResult:
    lowered = review_text.lower()
    approved = "error" not in lowered and len(review_text.strip()) > 0
    return ReviewResult(
        subtask_id="",
        approved=approved,
        feedback="[mock-llm] looks reasonable" if approved else "[mock-llm] output contained an error marker",
        quality_score=0.8 if approved else 0.3,
    )