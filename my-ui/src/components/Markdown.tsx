import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

const components: Components = {
  h1: (props) => (
    <h1 className="mb-3 mt-6 text-xl font-semibold text-slate-900 first:mt-0" {...props} />
  ),
  h2: (props) => (
    <h2 className="mb-2 mt-5 text-lg font-semibold text-slate-900 first:mt-0" {...props} />
  ),
  h3: (props) => (
    <h3 className="mb-2 mt-4 text-base font-semibold text-slate-900 first:mt-0" {...props} />
  ),
  p: (props) => <p className="mb-3 text-sm leading-relaxed text-slate-700 last:mb-0" {...props} />,
  ul: (props) => (
    <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-slate-700" {...props} />
  ),
  ol: (props) => (
    <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-slate-700" {...props} />
  ),
  li: (props) => <li className="leading-relaxed" {...props} />,
  strong: (props) => <strong className="font-semibold text-slate-900" {...props} />,
  a: (props) => (
    <a
      className="text-indigo-600 underline decoration-indigo-300 underline-offset-2 hover:text-indigo-500"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
  pre: (props) => (
    <pre className="mb-3 overflow-auto rounded-lg bg-slate-900 p-3 text-slate-100" {...props} />
  ),
  code: ({ className, children, ...props }) => {
    const text = String(children).replace(/\n$/, "");
    if (text.includes("\n")) {
      return (
        <code className={`font-mono text-xs ${className ?? ""}`} {...props}>
          {text}
        </code>
      );
    }
    return (
      <code
        className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs text-slate-800"
        {...props}
      >
        {text}
      </code>
    );
  },
  table: (props) => (
    <div className="mb-3 overflow-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  thead: (props) => <thead className="bg-slate-100" {...props} />,
  th: (props) => (
    <th className="border border-slate-200 px-3 py-1.5 text-left font-semibold text-slate-700" {...props} />
  ),
  td: (props) => <td className="border border-slate-200 px-3 py-1.5 text-slate-700" {...props} />,
  hr: (props) => <hr className="my-4 border-slate-200" {...props} />,
  blockquote: (props) => (
    <blockquote className="mb-3 border-l-4 border-slate-200 pl-3 italic text-slate-600" {...props} />
  ),
};

export default function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {children}
    </ReactMarkdown>
  );
}
