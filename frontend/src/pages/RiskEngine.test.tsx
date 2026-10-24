import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/services/api", () => ({ getIncidents: vi.fn() }));
import { getIncidents } from "@/services/api";
import RiskEngine from "@/pages/RiskEngine";
import type { Incident } from "@/types/incident";

const inc = (id: string, risk: number | null, severity: Incident["severity"] = "high"): Incident => ({
  id: 1, incident_id: id, title: `Title ${id}`, incident_type: "account_compromise", severity, status: "open",
  primary_username: null, primary_source_ip: null, primary_hostname: null, first_seen: "2026-10-01T00:00:00Z",
  last_seen: "2026-10-01T00:00:00Z", alert_count: 1, risk_score: risk, incident_metadata: {}, created_at: "2026-10-01T00:00:00Z",
});

const renderPage = () => render(<MemoryRouter><RiskEngine /></MemoryRouter>);

describe("RiskEngine page", () => {
  it("explains the five factors, which total 100", () => {
    vi.mocked(getIncidents).mockResolvedValue([]);
    renderPage();
    for (const f of ["Severity", "Asset criticality", "Detection confidence", "Correlated alerts", "ML anomaly"]) {
      expect(screen.getByText(f)).toBeInTheDocument();
    }
    expect(screen.getByText("Total").closest("tr")).toHaveTextContent("100");
  });

  it("ranks incidents from highest risk to lowest and links to each one", async () => {
    vi.mocked(getIncidents).mockResolvedValue([inc("INC-1001", 40), inc("INC-1002", 90), inc("INC-1003", 65)]);
    renderPage();
    await screen.findByText("INC-1002");
    const order = screen.getAllByRole("link").map((a) => a.textContent);
    expect(order).toEqual(["INC-1002", "INC-1003", "INC-1001"]);
    expect(screen.getByRole("link", { name: "INC-1002" })).toHaveAttribute("href", "/incidents/INC-1002");
    expect(screen.getByText("90/100")).toBeInTheDocument();
  });

  it("puts unscored incidents last and says so", async () => {
    vi.mocked(getIncidents).mockResolvedValue([inc("INC-1001", null), inc("INC-1002", 10)]);
    renderPage();
    await screen.findByText("INC-1002");
    expect(screen.getAllByRole("link").map((a) => a.textContent)).toEqual(["INC-1002", "INC-1001"]);
    expect(screen.getByText("not scored")).toBeInTheDocument();
  });

  it("has a helpful empty state", async () => {
    vi.mocked(getIncidents).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/No incidents yet/)).toBeInTheDocument();
  });
});
