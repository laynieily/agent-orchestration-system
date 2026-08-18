import { Link } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow px-6 py-4 flex gap-6">
        <Link to="/" className="text-blue-600 font-medium">
          Dashboard
        </Link>

        <Link to="/approvals" className="text-blue-600 font-medium">
          Approvals
        </Link>

        <Link to="/escalations" className="text-blue-600 font-medium">
          Escalations
        </Link>

        <Link to="/chat" className="text-blue-600 font-medium">
          Chat
        </Link>
      </nav>

      <main className="p-6">{children}</main>
    </div>
  );
}
