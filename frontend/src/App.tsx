import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Ingest } from "./pages/Ingest";
import { Review } from "./pages/Review";
import { Clusters } from "./pages/Clusters";
import { Codes } from "./pages/Codes";
import { Audit } from "./pages/Audit";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/ingest" element={<Ingest />} />
        <Route path="/review" element={<Review />} />
        <Route path="/clusters" element={<Clusters />} />
        <Route path="/codes" element={<Codes />} />
        <Route path="/audit" element={<Audit />} />
      </Routes>
    </Layout>
  );
}
