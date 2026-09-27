import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import AppShell from "@/layouts/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import EventMonitor from "@/pages/EventMonitor";
import Demo from "@/pages/Demo";
import ComingSoon from "@/pages/ComingSoon";

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
              <Route
                path="/detection"
                element={
                  <ComingSoon
                    title="Detection Engine"
                    phaseNote="rule-based detection lands in Phase 5"
                  />
                }
              />
              <Route
                path="/ml"
                element={
                  <ComingSoon
                    title="ML Anomaly Detection"
                    phaseNote="the Isolation Forest model lands in Phase 6"
                  />
                }
              />
              <Route
                path="/alerts"
                element={
                  <ComingSoon
                    title="Alerts"
                    phaseNote="it lands alongside detection in Phase 5"
                  />
                }
              />
              <Route
                path="/incidents"
                element={
                  <ComingSoon
                    title="Incident Management"
                    phaseNote="the incident page lands in Phase 9"
                  />
                }
              />
              <Route
                path="/risk"
                element={
                  <ComingSoon
                    title="Risk Engine"
                    phaseNote="the explainable risk score lands in Phase 8"
                  />
                }
              />
              <Route
                path="/ai-analyst"
                element={
                  <ComingSoon
                    title="AI SOC Analyst"
                    phaseNote="the AI investigation flow lands in Phase 10"
                  />
                }
              />
              <Route
                path="/mitre"
                element={
                  <ComingSoon
                    title="MITRE ATT&CK"
                    phaseNote="technique mapping lands in Phase 11"
                  />
                }
              />
              <Route
                path="/threat-intel"
                element={
                  <ComingSoon
                    title="Threat Intelligence"
                    phaseNote="the mock threat-intel provider lands in a later phase"
                  />
                }
              />
              <Route
                path="/response"
                element={
                  <ComingSoon
                    title="Response Center"
                    phaseNote="simulated response actions land in Phase 12"
                  />
                }
              />
              <Route
                path="/audit"
                element={
                  <ComingSoon
                    title="Audit Logs"
                    phaseNote="audit logging lands in Phase 13"
                  />
                }
              />
              <Route
                path="/dataset"
                element={
                  <ComingSoon
                    title="Dataset & ML Training"
                    phaseNote="the dataset/training page lands in Phase 14"
                  />
                }
              />
              <Route path="/demo" element={<Demo />} />
              <Route
                path="/system-health"
                element={
                  <ComingSoon
                    title="System Health"
                    phaseNote="it lands in a later phase"
                  />
                }
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
