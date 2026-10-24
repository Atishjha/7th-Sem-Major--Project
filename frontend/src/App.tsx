import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import AppShell from "@/layouts/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import EventMonitor from "@/pages/EventMonitor";
import DetectionEngine from "@/pages/DetectionEngine";
import MlAnomalyDetection from "@/pages/MlAnomalyDetection";
import Alerts from "@/pages/Alerts";
import Incidents from "@/pages/Incidents";
import IncidentDetail from "@/pages/IncidentDetail";
import MitreAttack from "@/pages/MitreAttack";
import ResponseCenter from "@/pages/ResponseCenter";
import AuditLogs from "@/pages/AuditLogs";
import Dataset from "@/pages/Dataset";
import Demo from "@/pages/Demo";
import RiskEngine from "@/pages/RiskEngine";
import AiAnalyst from "@/pages/AiAnalyst";
import ThreatIntel from "@/pages/ThreatIntel";
import SystemHealth from "@/pages/SystemHealth";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path="/events" element={<EventMonitor />} />
              <Route path="/detection" element={<DetectionEngine />} />
              <Route path="/ml" element={<MlAnomalyDetection />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/incidents" element={<Incidents />} />
              <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
              <Route path="/risk" element={<RiskEngine />} />
              <Route path="/ai-analyst" element={<AiAnalyst />} />
              <Route path="/mitre" element={<MitreAttack />} />
              <Route path="/threat-intel" element={<ThreatIntel />} />
              <Route path="/response" element={<ResponseCenter />} />
              <Route path="/audit" element={<AuditLogs />} />
              <Route path="/dataset" element={<Dataset />} />
              <Route path="/demo" element={<Demo />} />
              <Route path="/system-health" element={<SystemHealth />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
