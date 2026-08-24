// Shared className strings so buttons, cards, badges, and inputs read
// consistently across Dashboard / Approvals / Escalations / Chat.

const buttonBase =
  "inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50";

export const button = {
  primary: `${buttonBase} bg-indigo-600 text-white hover:bg-indigo-500 active:bg-indigo-700`,
  secondary: `${buttonBase} border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 active:bg-slate-100`,
  success: `${buttonBase} bg-emerald-600 text-white hover:bg-emerald-500 active:bg-emerald-700`,
  danger: `${buttonBase} bg-red-600 text-white hover:bg-red-500 active:bg-red-700`,
};

export const card =
  "rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md";

export const input =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm transition placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30";

export const emptyState =
  "rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center text-sm text-slate-500";

export function statusBadgeClass(status: string): string {
  switch (status) {
    case "done":
      return "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20";
    case "paused":
      return "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20";
    case "aborted":
    case "plan_rejected":
      return "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20";
    default:
      return "bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-500/15";
  }
}
