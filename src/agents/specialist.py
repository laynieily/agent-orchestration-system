"""
Specialist agents: each is a function scoped to one domain and a slice of
the tool registry. Takes a SubTask + completed results + reviewer feedback
(on retry), returns a SpecialistResult.
"""
from __future__ import annotations

from typing import Callable, Optional

from src.schemas.models import SpecialistName, SpecialistResult, SubTask, ToolCallLog
from src.tools.registry import ToolError, ToolRegistry


def _gather_context(subtask: SubTask, completed: dict) -> str:
    blocks = []
    for dep_id in subtask.depends_on:
        dep = completed.get(dep_id)
        if dep:
            blocks.append(f"[{dep.specialist.value} output for {dep_id}]\n{dep.output}")
    return "\n\n".join(blocks)


def research_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry, llm, 
                        feedback: Optional[str] = None) -> SpecialistResult:
    try: 
        log = tools.invoke(
            "web_search",
            agent = SpecialistName.RESEARCHER.value,
            query=subtask.description,
            max_results=5,
        )
        # readible output
        lines = []
        for item in log.output:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            lines.append(f"- {title}: {snippet}")

        output = "\n".join(lines)

        return SpecialistResult(
            subtask_id=subtask.id,
            specialist=SpecialistName.RESEARCHER,
            output=output,
            tool_calls=[log],
            success = True,
            error=None,
        )
    except ToolError as exc:
        return SpecialistResult(
            subtask_id=subtask.id,
            specialist= SpecialistName.RESEARCHER,
            output= "",
            tool_calls=[],
            success=False,
            error=str(exc),
        )



def data_analysis_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry,
                              llm, feedback: Optional[str] = None) -> SpecialistResult:
    context = _gather_context(subtask, completed)

    try:
        lines = [ln for ln in context.splitlines() if ln.strip()]
        non_empty_count = len(lines)
        key_insight = lines[0] if lines else "No context available."

        output = (
            f"Non-empty lines: {non_empty_count}\n"
            f"Key insight: {key_insight}"
        )

        return SpecialistResult(
            subtask_id=subtask.id,
            specialist=SpecialistName.DATA_ANALYSIS,
            output=output,
            tool_calls=[],
            success=True, 
            error=None,
        )

    except Exception as exc:
        return SpecialistResult (
            subtask_id=subtask.id,
            specialist=SpecialistName.DATA_ANALYSIS,
            output="",
            tool_calls=[],
            success=False,
            error=str(exc),
        )


def writing_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry,
                        llm, feedback: Optional[str] = None) -> SpecialistResult:
    context = _gather_context(subtask, completed)
    prompt = (
        f"Context:\n{context}\n\n"
        f"Expected ouput format:\n{subtask.expected_output_format}\n\n"
    ) 
    
    if feedback:
        prompt+= f"Reviewer feedback to address: \n{feedback}\n"

    raw = llm.invoke(prompt)
    text = getattr(raw, "content", raw)

    return SpecialistResult(
        subtask_id=subtask.id,
        specialist=SpecialistName.WRITER,
        output=str(text),
        tool_calls=[],
        success=True,
        error = None,
    )


def code_execution_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry,
                               llm, feedback: Optional[str] = None) -> SpecialistResult:
    code = f"print('Task: {subtask.description}')"

    try: 
        log = tools.invoke(
            "code_execution",
            agent=SpecialistName.CODE_EXECUTION.value,
            code=code,
            timeout_s=5,
        )

        stdout = log.output.get("stdout", "")
        returncode = log.output.get("returncode")

        success = returncode == 0
        output = f"stdout: \n{stdout}\nreturncode: {returncode}"

        return SpecialistResult(
            subtask_id = subtask.id,
            specialist=SpecialistName.CODE_EXECUTION,
            output=output,
            tool_calls=[log],
            success=success,
            error=None if success else "Non-zero return code.",
        )

    except ToolError as exc:
        return SpecialistResult(
            subtask_id=subtask.id,
            specialist=SpecialistName.CODE_EXECUTION,
            output = "",
            tool_calls=[],
            success=False,
            error=str(exc),
        )


SPECIALIST_DISPATCH: dict[SpecialistName, Callable] = {
    SpecialistName.RESEARCHER: research_specialist,
    SpecialistName.DATA_ANALYSIS: data_analysis_specialist,
    SpecialistName.WRITER: writing_specialist,
    SpecialistName.CODE_EXECUTION: code_execution_specialist,
}