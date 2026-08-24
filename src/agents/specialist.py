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


def _extract_text(raw) -> str:
    """
    Pull plain text out of an LLM response. With extended/adaptive thinking
    enabled, ChatAnthropic's `.content` is a list of content blocks (a
    "thinking" block plus a "text" block), not a plain string -- naively
    str()-ing that list dumps the raw block reprs (base64 thinking signature
    included) into the output. Keep only the text blocks.
    """
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


def _generate_search_queries(subtask: SubTask, llm, feedback: Optional[str]) -> list[str]:
    prompt = (
        f"Research task:\n{subtask.description}\n\n"
        + (
            f"A prior attempt was rejected with this feedback -- make sure your "
            f"queries target the gaps it names:\n{feedback}\n\n"
            if feedback else ""
        )
        + "Break this into 3-4 short, specific web search queries (a few words "
          "each, like something you'd actually type into a search engine) that "
          "together would surface authoritative sources (official docs, vendor "
          "docs, credible technical writeups) covering the task. Reply with "
          "ONLY the queries, one per line, no numbering or extra commentary."
    )
    raw = llm.invoke(prompt)
    queries = [q.strip("-•* \t") for q in _extract_text(raw).splitlines() if q.strip()]
    return queries[:4] or [subtask.description[:200]]


def research_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry, llm,
                        feedback: Optional[str] = None) -> SpecialistResult:
    # A single search using the raw (often paragraph-length) subtask
    # description as the query tends to surface generic/low-authority
    # results, and since the query never changes, retries just re-synthesize
    # the same thin data. Search multiple focused queries instead, and let
    # feedback steer new queries on retry so a retry can actually find
    # something new rather than only rephrase the same material.
    queries = _generate_search_queries(subtask, llm, feedback)

    tool_calls: list[ToolCallLog] = []
    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in queries:
        try:
            log = tools.invoke(
                "web_search",
                agent=SpecialistName.RESEARCHER.value,
                query=query,
                max_results=5,
            )
            tool_calls.append(log)
            for item in log.output:
                url = item.get("url", "")
                if url and url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(item)
        except ToolError:
            continue  # one bad query shouldn't sink the whole subtask

    if not results:
        return SpecialistResult(
            subtask_id=subtask.id,
            specialist=SpecialistName.RESEARCHER,
            output="",
            tool_calls=tool_calls,
            success=False,
            error="All searches failed or returned no results.",
        )

    raw_results = "\n".join(
        f"- {item.get('title', '')}: {item.get('snippet', '')} ({item.get('url', '')})"
        for item in results
    )

    # Raw search snippets are thin (one line each) and rarely match an
    # ambitious expected_output_format (e.g. "20+ bullets across 5
    # topic headings, each with a source") on their own -- synthesize
    # them into the actual requested structure instead of dumping them.
    prompt = (
        f"Research task:\n{subtask.description}\n\n"
        f"Expected output format:\n{subtask.expected_output_format}\n\n"
        f"Raw search results:\n{raw_results}\n\n"
        "Write up the findings in the expected output format, grounded "
        "only in the search results above -- cite the source URL next "
        "to each fact and don't invent sources. If the results are too "
        "thin to fully cover the task, say so explicitly rather than "
        "padding with unsupported claims."
    )
    if feedback:
        prompt += f"\nReviewer feedback to address: \n{feedback}\n"

    raw = llm.invoke(prompt)
    output = _extract_text(raw)

    return SpecialistResult(
        subtask_id=subtask.id,
        specialist=SpecialistName.RESEARCHER,
        output=output,
        tool_calls=tool_calls,
        success=True,
        error=None,
    )



def data_analysis_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry,
                              llm, feedback: Optional[str] = None) -> SpecialistResult:
    context = _gather_context(subtask, completed)
    prompt = (
        f"Context:\n{context}\n\n"
        f"Analysis task:\n{subtask.description}\n\n"
        f"Expected output format:\n{subtask.expected_output_format}\n\n"
    )

    if feedback:
        prompt += f"Reviewer feedback to address: \n{feedback}\n"

    try:
        raw = llm.invoke(prompt)
        text = _extract_text(raw)

        return SpecialistResult(
            subtask_id=subtask.id,
            specialist=SpecialistName.DATA_ANALYSIS,
            output=text,
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
    text = _extract_text(raw)

    return SpecialistResult(
        subtask_id=subtask.id,
        specialist=SpecialistName.WRITER,
        output=text,
        tool_calls=[],
        success=True,
        error = None,
    )


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[: -len("```")]
    return text.strip()


def code_execution_specialist(subtask: SubTask, completed: dict, tools: ToolRegistry,
                               llm, feedback: Optional[str] = None) -> SpecialistResult:
    context = _gather_context(subtask, completed)
    prompt = (
        f"Context:\n{context}\n\n"
        f"Task:\n{subtask.description}\n\n"
        f"Expected output format:\n{subtask.expected_output_format}\n\n"
        "Write a short, self-contained Python script that accomplishes this task "
        "and prints its result. Respond with ONLY the Python source code -- no "
        "explanation, no markdown code fences."
    )

    if feedback:
        prompt += f"\nReviewer feedback to address: \n{feedback}\n"

    raw = llm.invoke(prompt)
    code = _strip_code_fences(_extract_text(raw))

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
        output = f"```python\n{code}\n```\n\nstdout:\n{stdout}\nreturncode: {returncode}"

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