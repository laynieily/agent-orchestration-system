import { useEffect, useState } from "react";
import { useTaskEvents } from "../hooks/useTaskEvents";
import { CheckIcon, PencilIcon, TakeOverIcon, XIcon } from "../components/icons";
import ProgressTracker, { type ApprovalProgress } from "../components/review/ProgressTracker";
import MemoryPanel, { type MemoryEntry } from "../components/review/MemoryPanel";
import AskPanel from "../components/review/AskPanel";
import { button, card, emptyState, input } from "../lib/styles";

const API_BASE = "http://127.0.0.1:8001"; // TODO: swap for a Vite proxy path if you set one up later

interface ApprovalSummary {
  id: string;
  task_id: string;
  level: "approve_plan" | "approve_action" | "notify" | "take_over";
  reason: string;
  created_at: number;
}

interface ApprovalDetail extends ApprovalSummary {
  context: Record<string, any>;
  resolution: string | null;
  resolution_notes: string | null;
}

type EditMode = "modify" | "takeover" | null;

export default function Approvals() {
  const [items, setItems] = useState<ApprovalSummary[]>([]);
  const [details, setDetails] = useState<Record<string, ApprovalDetail>>({});
  const [progress, setProgress] = useState<Record<string, ApprovalProgress>>({});
  const [memories, setMemories] = useState<Record<string, MemoryEntry[]>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [outputs, setOutputs] = useState<Record<string, string>>({});
  const [planEdits, setPlanEdits] = useState<Record<string, string>>({});
  const [editMode, setEditMode] = useState<Record<string, EditMode>>({});
  const [resolving, setResolving] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchApprovals();
  }, []);

  useTaskEvents(() => fetchApprovals());

  function fetchApprovals() {
    fetch(`${API_BASE}/approvals`)
      .then((res) => res.json())
      .then((data: ApprovalSummary[]) => {
        setItems(data);
        data.forEach((item) => {
          fetchDetail(item.id);
          fetchProgress(item.id);
          fetchMemories(item.id);
        });
      });
  }

  function fetchDetail(id: string) {
    fetch(`${API_BASE}/approvals/${id}`)
      .then((res) => res.json())
      .then((data: ApprovalDetail) => {
        setDetails((prev) => ({ ...prev, [id]: data }));
        if (data.level === "approve_plan" && data.context?.plan) {
          setPlanEdits((prev) =>
            prev[id] !== undefined
              ? prev
              : { ...prev, [id]: JSON.stringify(data.context.plan, null, 2) }
          );
        }
        if (data.level === "approve_action" && typeof data.context?.last_output === "string") {
          setOutputs((prev) =>
            prev[id] !== undefined ? prev : { ...prev, [id]: data.context.last_output }
          );
        }
      });
  }

  function fetchProgress(id: string) {
    fetch(`${API_BASE}/approvals/${id}/progress`)
      .then((res) => res.json())
      .then((data: ApprovalProgress) => setProgress((prev) => ({ ...prev, [id]: data })))
      .catch((err) => console.error("failed to load progress", err));
  }

  function fetchMemories(id: string) {
    fetch(`${API_BASE}/approvals/${id}/memories`)
      .then((res) => res.json())
      .then((data: MemoryEntry[]) => setMemories((prev) => ({ ...prev, [id]: data })))
      .catch((err) => console.error("failed to load memories", err));
  }

  function resolve(
    id: string,
    decision: string,
    extra?: { output?: string; edited_plan?: unknown }
  ) {
    if (resolving[id]) return; // already in flight -- ignore a duplicate click

    setResolving((prev) => ({ ...prev, [id]: true }));

    fetch(`${API_BASE}/approvals/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        notes: notes[id] ?? "",
        output: extra?.output ?? null,
        edited_plan: extra?.edited_plan ?? null,
      }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.text();
          throw new Error(`resolve failed (${res.status}): ${err}`);
        }
        return res.json();
      })
      .then((result) => {
        console.log("resolve result:", result); // status, final_output, pending_approval_id
        setItems((prev) => prev.filter((i) => i.id !== id));
      })
      .catch((err) => {
        console.error(err);
        alert(err.message); // swap for a nicer toast later
      })
      .finally(() => {
        setResolving((prev) => ({ ...prev, [id]: false }));
      });
  }

  function submitPlanEdit(id: string) {
    try {
      const edited_plan = JSON.parse(planEdits[id] ?? "");
      resolve(id, "take_over", { edited_plan });
    } catch {
      alert("Plan JSON is invalid — fix it before submitting.");
    }
  }

  function openEdit(id: string, mode: EditMode, isPlanLevel: boolean, blankTemplate: string) {
    setEditMode((prev) => ({ ...prev, [id]: mode }));
    if (mode === "takeover") {
      // Take Over starts from a blank slate; Modify keeps whatever's there
      // (already pre-filled with the agent's draft when the detail loaded).
      if (isPlanLevel) {
        setPlanEdits((prev) => ({ ...prev, [id]: blankTemplate }));
      } else {
        setOutputs((prev) => ({ ...prev, [id]: "" }));
      }
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Approval Queue
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Tasks paused for a human decision.
        </p>
      </div>

      {items.length === 0 && (
        <div className={emptyState}>No pending approvals.</div>
      )}

      <div className="space-y-4">
        {items.map((item) => {
          const detail = details[item.id];
          const itemProgress = progress[item.id];
          const itemMemories = memories[item.id] ?? [];
          const isPlanLevel = item.level === "approve_plan";
          const isResolving = resolving[item.id] ?? false;
          const mode = editMode[item.id] ?? null;
          const subtask = detail?.context?.subtask;
          const lastOutput = detail?.context?.last_output as string | undefined;
          const lastFeedback = detail?.context?.last_feedback as string | undefined;

          return (
            <div key={item.id} className={card}>
              {/* Decision point */}
              <div className="mb-3 flex items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-slate-900">
                  Task {item.task_id}
                </h2>
                <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 ring-1 ring-inset ring-slate-500/15">
                  {item.level}
                </span>
              </div>
              <p className="mb-4 text-sm text-slate-700">
                <span className="font-medium text-slate-900">Decision needed: </span>
                {item.reason}
              </p>

              {/* Task context + execution progress */}
              {itemProgress && (
                <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <ProgressTracker progress={itemProgress} />
                </div>
              )}

              {/* Agent's proposed action + reasoning (subtask-level; for
                  plan-level this is already the progress/rationale above) */}
              {!isPlanLevel && subtask && (
                <div className="mb-4">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Agent's proposed action
                  </p>
                  <p className="mb-2 text-sm text-slate-700">
                    <span className="font-medium text-slate-900">Asked to: </span>
                    {subtask.description}
                  </p>
                  {lastOutput && (
                    <pre className="mb-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                      {lastOutput}
                    </pre>
                  )}
                  {lastFeedback && (
                    <p className="text-sm text-slate-600">
                      <span className="font-medium text-slate-900">
                        Reviewer's reasoning for rejecting it:{" "}
                      </span>
                      {lastFeedback}
                    </p>
                  )}
                </div>
              )}

              {/* Relevant memories / past similar decisions */}
              <div className="mb-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Relevant past decisions
                </p>
                <MemoryPanel memories={itemMemories} />
              </div>

              {/* Ask the agent clarifying questions before deciding */}
              <div className="mb-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Ask before deciding
                </p>
                <AskPanel apiBase={API_BASE} approvalId={item.id} />
              </div>

              <textarea
                placeholder="Optional notes"
                className={`${input} mb-3`}
                value={notes[item.id] ?? ""}
                onChange={(e) =>
                  setNotes({ ...notes, [item.id]: e.target.value })
                }
              />

              {/* Edit panel, opened by Modify or Take Over */}
              {mode && (
                <div className="mb-3">
                  <label
                    htmlFor={`edit-${item.id}`}
                    className="mb-1 block text-xs font-medium text-slate-500"
                  >
                    {isPlanLevel
                      ? mode === "modify"
                        ? "Modify the plan JSON, then submit"
                        : "Write a replacement plan JSON from scratch, then submit"
                      : mode === "modify"
                      ? "Modify the agent's output, then submit"
                      : "Write a replacement output from scratch, then submit"}
                  </label>
                  <textarea
                    id={`edit-${item.id}`}
                    className={`${input} mb-2 ${isPlanLevel ? "h-56 font-mono text-xs" : ""}`}
                    spellCheck={false}
                    value={(isPlanLevel ? planEdits[item.id] : outputs[item.id]) ?? ""}
                    onChange={(e) =>
                      isPlanLevel
                        ? setPlanEdits({ ...planEdits, [item.id]: e.target.value })
                        : setOutputs({ ...outputs, [item.id]: e.target.value })
                    }
                  />
                  <div className="flex gap-3">
                    <button
                      type="button"
                      disabled={isResolving}
                      onClick={() =>
                        isPlanLevel
                          ? submitPlanEdit(item.id)
                          : resolve(item.id, "take_over", { output: outputs[item.id] ?? "" })
                      }
                      className={button.primary}
                    >
                      Submit
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditMode((prev) => ({ ...prev, [item.id]: null }))}
                      className={button.secondary}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Action buttons */}
              {!mode && (
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    disabled={isResolving}
                    onClick={() => resolve(item.id, isPlanLevel ? "approved" : "accept")}
                    className={button.success}
                  >
                    <CheckIcon className="h-4 w-4" />
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={isResolving}
                    onClick={() => openEdit(item.id, "modify", isPlanLevel, "")}
                    className={button.primary}
                  >
                    <PencilIcon className="h-4 w-4" />
                    Modify
                  </button>
                  <button
                    type="button"
                    disabled={isResolving}
                    onClick={() =>
                      openEdit(
                        item.id,
                        "takeover",
                        isPlanLevel,
                        JSON.stringify({ subtasks: [], confidence: 1, rationale: "" }, null, 2)
                      )
                    }
                    className={button.secondary}
                  >
                    <TakeOverIcon className="h-4 w-4" />
                    Take Over
                  </button>
                  {isPlanLevel && (
                    <button
                      type="button"
                      disabled={isResolving}
                      onClick={() => resolve(item.id, "rejected")}
                      className={button.secondary}
                    >
                      Reject
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={isResolving}
                    onClick={() => resolve(item.id, "abort")}
                    className={button.danger}
                  >
                    <XIcon className="h-4 w-4" />
                    Abort
                  </button>
                  {isResolving && (
                    <span className="text-sm text-slate-500">
                      Working — this can take a while with a real model, please don't click twice…
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
