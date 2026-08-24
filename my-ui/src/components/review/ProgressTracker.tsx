import { CheckIcon, ClockIcon } from "../icons";

export interface SubtaskProgress {
  id: string;
  description: string;
  assigned_specialist: string;
  status: "completed" | "current" | "pending";
}

export interface ApprovalProgress {
  original_request: string;
  plan_confidence: number | null;
  plan_rationale: string | null;
  subtasks: SubtaskProgress[];
  completed_count: number;
  total_count: number;
}

function StepIcon({ status }: { status: SubtaskProgress["status"] }) {
  if (status === "completed") {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
        <CheckIcon className="h-3 w-3" />
      </span>
    );
  }
  if (status === "current") {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700">
        <ClockIcon className="h-3 w-3" />
      </span>
    );
  }
  return <span className="h-5 w-5 shrink-0 rounded-full border-2 border-slate-200" />;
}

export default function ProgressTracker({ progress }: { progress: ApprovalProgress }) {
  return (
    <div>
      <p className="text-sm text-slate-700">
        <span className="font-medium text-slate-900">Request: </span>
        {progress.original_request}
      </p>

      {progress.plan_rationale && (
        <p className="mt-2 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Agent's plan reasoning: </span>
          {progress.plan_rationale}
          {progress.plan_confidence != null && (
            <span className="ml-1 text-slate-500">
              (confidence {progress.plan_confidence.toFixed(2)})
            </span>
          )}
        </p>
      )}

      {progress.total_count > 0 && (
        <div className="mt-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Execution progress — {progress.completed_count}/{progress.total_count} subtasks done
          </p>
          <ol className="space-y-2">
            {progress.subtasks.map((sub) => (
              <li key={sub.id} className="flex items-start gap-2">
                <StepIcon status={sub.status} />
                <div className="min-w-0">
                  <p
                    className={`text-sm leading-snug ${
                      sub.status === "pending" ? "text-slate-400" : "text-slate-700"
                    }`}
                  >
                    {sub.description}
                  </p>
                  <p className="text-xs text-slate-400">{sub.assigned_specialist}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
