import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Approvals from "./pages/Approvals";
import Escalations from "./pages/Escalations";
import Layout from "./components/Layout";
import Chat from "./pages/Chat";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/escalations" element={<Escalations />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
