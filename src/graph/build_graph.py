# ----------------------------- GRAPH LAYOUT -----------------------------

# intake -> planning -[confidence low]-> escalate_plan -> dispatch
#                     -[confidence ok]-------------------> dispatch

# dispatch -[subtask ready]-> specialist_exec -> review
#          -[all done]------> synthesis -> delivery -> END

# review -[approved]--------------------> dispatch
#        -[rejected, retries left]------> specialist_exec (retry, with feedback)
#        -[rejected, retries exhausted]-> escalate_subtask -> dispatch

# ------------------------------------------------------------------------

"""
Wires Supervisor / Specialist / Reviewer into a LangGraph StateGraph.
"""
from __future__ import annotations

import os
from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.reviewer import ReviewerAgent
from src.agents.specialist import SPECIALIST_DISPATCH
from src.agents.supervisor import SupervisorAgent
from src.graph.state import OrchestratorState
from src.schemas.models import ApprovalLevel, EscalationEvent, SpecialistResult
from src.tools.registry import ToolRegistry

from src.memory.working_memory import WorkingMemoryStore


PLAN_CONFIDENCE_THRESHOLD = float(os.getenv("PLAN_CONFIDENCE_THRESHOLD", "0.6"))
MAX_SUBTASK_RETRIES = int(os.getenv("MAX_SUBTASK_RETRIES", "2"))


def build_graph(tools: ToolRegistry, memory: WorkingMemoryStore, planner_llm, specialist_llm, reviewer_llm):
    supervisor = SupervisorAgent(planner_llm)
    reviewer = ReviewerAgent(reviewer_llm)

    # ---- nodes ----------------------------------------------------------
    # Each node takes the current state dict and returns a dict of ONLY the
    # keys it's changing -- LangGraph merges your return value into the
    # running state, you don't need to return the whole thing back.

    def intake(state: OrchestratorState) -> dict:
        return { 
            "completed": {}, 
            "reviews": {}, 
            "retries": {}, 
            "escalations": [], 
            "status": "planning",
        }

    def planning(state: OrchestratorState) -> dict:
        plan = supervisor.create_plan(state["original_request"])
        memory.set(plan.task_id, "plan", plan.model_dump())
        return {
            "plan": plan, 
            "task_id": plan.task_id, 
            "status": "running",
        }
    

    def escalate_plan(state: OrchestratorState) -> dict:
        plan = state["plan"]
        event = EscalationEvent(
            task_id=plan.task_id,
            reason=f"Plan confidence {plan.confidence} < threshold {PLAN_CONFIDENCE_THRESHOLD}",
            level= ApprovalLevel.APPROVE_PLAN,
            context={"plan": plan.model_dump()},
            resolution="auto",
            resolution_notes="Phase 1 stub: auto-approved plan despite low confidence.",
        )
        return { "escalations": state.get("escalations", []) + [event] }
    

    def dispatch(state: OrchestratorState) -> dict:
        plan = state["plan"]
        completed = state.get("completed", {})
        ready = plan.ready_subtasks(set(completed.keys()))
        if ready: 
            return {"current_subtask_id": ready[0].id}
        return {"current_subtask_id": None}


    def specialist_exec(state: OrchestratorState) -> dict:
        plan = state["plan"]
        subtask = plan.subtask_by_id(state["current_subtask_id"])

        # if previous atempt failed provide with reviewer feedback
        prev_review = state.get("reviews", {}).get(subtask.id)
        feedback = prev_review.feedback if prev_review and not prev_review.approved else None

        fn = SPECIALIST_DISPATCH[subtask.assigned_specialist]
        result = fn(
            subtask,
            state.get("completed", {}),
            tools,
            specialist_llm,
            feedback=feedback,
        )
        return {"pending_result": result}
        
    def review(state: OrchestratorState) -> dict:
        plan = state["plan"]
        subtask = plan.subtask_by_id(state["current_subtask_id"])
        result = state["pending_result"]

        review_result = reviewer.review(subtask, result)

        reviews = dict(state.get("reviews", {})) 
        reviews[subtask.id] = review_result
        
        if review_result.approved:
            completed = dict(state.get("completed", {}))
            completed[subtask.id] = result
            memory.append_log(plan.task_id, "completed subtasks", subtask.id)
            return {"reviews": reviews, "completed": completed}
        
        #rejected
        memory.append_log(plan.task_id, "error logs", review_result.feedback)
        retries = dict(state.get("retries", {}))
        retries[subtask.id] = retries.get(subtask.id, 0) + 1
        return {"reviews": reviews, "retries": retries}


    def escalate_subtask(state: OrchestratorState) -> dict:
        subtask_id = state["current_subtask_id"]
        plan = state["plan"]
        subtask = plan.subtask_by_id(subtask_id)

        last_review = state["reviews"][subtask_id]
        last_result = state["pending_result"]

        event = EscalationEvent(
            task_id=plan.task_id,
            reason=f"Subtask {subtask_id} exceeded retry limit ({MAX_SUBTASK_RETRIES})",
            level=ApprovalLevel.APPROVE_ACTION,
            context={
                "subtask": subtask.model_dump(),
                "last_output": last_result.output,
                "last_feedback": last_review.feedback,
            },
            resolution="auto",
            resolution_notes="Phase 1 stub: auto-accepted best effort result.",
        ) 
        memory.append_log(plan.task_id, "error_logs", f"Escalated: {event.reason}")
        
        completed = dict(state.get("completed", {}))
        completed[subtask_id] = last_result

        return {"completed": completed, "current_subtask_id": None, "escalations": state.get("escalations", []) + [event]}
        

    def synthesis(state: OrchestratorState) -> dict:
        final = supervisor.synthesize(state["plan"], state.get("completed", {}))
        return {"final_output": final, "status": "done"}

    def delivery(state: OrchestratorState) -> dict:
        memory.clear(state["plan"].task_id)
        return {}

    # routing functions
    # These decide which edge to follow. They take the state AFTER the
    # preceding node ran, and return the name of the next node as a string.

    def route_after_planning(state: OrchestratorState) -> Literal["escalate_plan", "dispatch"]:
        return "escalate_plan" if state["plan"].confidence < PLAN_CONFIDENCE_THRESHOLD else "dispatch"
        

    def route_after_dispatch(state: OrchestratorState) -> Literal["specialist_exec", "synthesis"]:
        return "specialist_exec" if state.get("current_subtask_id") else "synthesis"

    def route_after_review(state: OrchestratorState) -> Literal["dispatch", "specialist_exec", "escalate_subtask"]:
        subtask_id = state["current_subtask_id"]
        review_result = state["reviews"][subtask_id]
        if review_result.approved: return "dispatch"
        if state["retries"].get(subtask_id, 0) >= MAX_SUBTASK_RETRIES: return "escalate_subtask"
        return "specialist_exec"
    

    # graph assembly 

    graph = StateGraph(OrchestratorState)

    graph.add_node("intake", intake)
    graph.add_node("planning", planning)
    graph.add_node("escalate_plan", escalate_plan)
    graph.add_node("dispatch", dispatch)
    graph.add_node("specialist_exec", specialist_exec)
    graph.add_node("review", review)
    graph.add_node("escalate_subtask", escalate_subtask)
    graph.add_node("synthesis", synthesis)
    graph.add_node("delivery", delivery)

    graph.set_entry_point("intake")

    graph.add_edge("intake", "planning")
    graph.add_conditional_edges(
        "planning",
        route_after_planning, {
            "escalate_plan": "escalate_plan",
            "dispatch" : "dispatch", 
        },
    )

    graph.add_edge("escalate_plan", "dispatch")
    graph.add_conditional_edges(
            "dispatch",
            route_after_dispatch, {
                "specialist_exec": "specialist_exec",
                "synthesis" : "synthesis", 
            },
        )

    graph.add_edge("specialist_exec", "review")

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "dispatch": "dispatch",
            "specialist_exec": "specialist_exec",
            "escalate_subtask": "escalate_subtask",
        },
    )

    graph.add_edge("escalate_subtask", "dispatch")
    graph.add_edge("synthesis", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile()


def run_task(request: str, tools: ToolRegistry, memory: WorkingMemoryStore, planner_llm, specialist_llm, reviewer_llm,
             recursion_limit: int = 50) -> OrchestratorState:
    app = build_graph(tools, memory, planner_llm, specialist_llm, reviewer_llm)
    initial: OrchestratorState = {"original_request": request}
    return app.invoke(initial, config={"recursion_limit": recursion_limit})