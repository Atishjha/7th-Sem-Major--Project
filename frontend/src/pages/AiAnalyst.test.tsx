import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/services/api", () => ({ getIncidents: vi.fn() }));
import { getIncidents } from "@/services/api";
import AiAnalyst from "@/pages/AiAnalyst";

const renderPage = () => render(<MemoryRouter><AiAnalyst /></MemoryRouter>);

describe("AiAnalyst page", () => {
  it("lists incidents with a link into each investigation", async () => {
    vi.mocked(getIncidents).mockResolvedValue([
      { incident_id: "INC-1001", title: "Possible Account Compromise (demo_user)", severity: "critical" } as never,
    ]);
    renderPage();
    expect(await screen.findByText("Possible Account Compromise (demo_user)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open investigation/ })).toHaveAttribute("href", "/incidents/INC-1001");
  });

  it("is upfront about how it works: evidence vs inference, offline default, fallback, advisory only", async () => {
    vi.mocked(getIncidents).mockResolvedValue([]);
    renderPage();
    expect(screen.getByText(/Facts and interpretation are kept apart/)).toBeInTheDocument();
    expect(screen.getByText(/Works offline by default/)).toBeInTheDocument();
    expect(screen.getByText(/Never leaves you without a report/)).toBeInTheDocument();
    expect(screen.getByText(/Advisory only/)).toBeInTheDocument();
    expect(await screen.findByText(/No incidents yet/)).toBeInTheDocument();
  });
});
