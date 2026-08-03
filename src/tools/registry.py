"""
Tool registry: tools are registered with a name, description, input/output
schemas, which specialist agents may use them, and a rate limit. Every
invocation is logged (inputs, output, latency, success/failure) via
ToolCallLog, regardless of which specialist called it.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel

from src.schemas.models import ToolCallLog


class ToolError(Exception):
    pass


class RateLimitExceeded(ToolError):
    pass


class NotAuthorized(ToolError):
    pass


@dataclass
class ToolSpec:
    name: str
    description: str
    func: Callable[..., Any]
    input_schema: type[BaseModel]
    allowed_agents: list[str]
    output_schema: Optional[type[BaseModel]] = None
    rate_limit_per_minute: int = 60
    # Tracks call timestamps per agent, for rate limiting. Not something
    # you pass in when creating a ToolSpec -- it's internal bookkeeping.
    _call_times: dict[str, deque] = field(default_factory=lambda: defaultdict(deque))

    def _check_rate_limit(self, agent: str) -> None:
        now = time.time()
        window = self._call_times[agent] # this agent's call history
        # 3. Purge stale entries: 
        while window and now - window[0] > 60:
            window.popleft()
        #    This keeps only calls from the last 60 seconds.
        if len(window) >= self.rate_limit_per_minute:
            raise RateLimitExceeded( f"Rate limit exceeded for tool '{self.name}' by agent '{agent}'.")
        # 5. Otherwise, record this call: 
        window.append(now)



class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self.call_log: list[ToolCallLog] = []

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise ToolError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_for_agent(self, agent_name: str) -> list[str]:
        return [
            spec.name
            for spec in self._tools.values()
            if agent_name in spec.allowed_agents or "*" in spec.allowed_agents
        ]

    def invoke(self, tool_name: str, agent: str, **kwargs: Any) -> ToolCallLog:
        # 1. lookup
        spec = self.get(tool_name)
        
        # 2. authorization check:
        if agent not in spec.allowed_agents and "*" not in spec.allowed_agents:
            raise NotAuthorized(
                f"Agent '{agent}' is not authorized to use tool '{tool_name}'."
            )
    
        # 3. rate limit
        spec._check_rate_limit(agent)
        
        # 4. validate inputs against the schema:
        validated = spec.input_schema(**kwargs)  #(this raises a pydantic ValidationError on its own if kwargs don't match)
        
        # 5. run tool
        start = time.perf_counter()
        success, error, output = True, None, None
        try:
            output = spec.func(**validated.model_dump())
        except Exception as exc:
            success = False
            error = f"{type(exc).__name__}: {exc}"

        latency_ms = (time.perf_counter() - start) * 1000
        
        # 6. log call
        log = ToolCallLog(
            tool_name=tool_name,
            agent=agent,
            inputs=kwargs,
            output=output,
            latency_ms=latency_ms,
            success=success,
            error=error,
        )
        self.call_log.append(log)
       
        
        # 7. raise if failed
        if not success: 
            raise ToolError(error)

        return log