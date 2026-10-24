import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/services/api", () => ({ getAuditLogs: vi.fn() }));
import { getAuditLogs } from "@/services/api";
import AuditLogs from "@/pages/AuditLogs";
import type { AuditLogEntry } from "@/types/audit";

const entry = (o: Partial<AuditLogEntry>): AuditLogEntry => ({
  id: 1, timestamp: "2026-10-01T10:00:00Z", username: "analyst", action: "Ran AI investigation",
  resource_type: "incident", resource_id: "INC-1001", old_value: null, new_value: { provider_used: "mock" }, result: "SUCCESS", ...o,
});

const renderPage = () => render(<MemoryRouter><AuditLogs /></MemoryRouter>);

describe("AuditLogs page", () => {
  it("shows a loading state, then the entries", async () => {
    vi.mocked(getAuditLogs).mockResolvedValue([entry({}), entry({ id: 2, username: "admin", action: "Updated detection rule 'Brute Force'", resource_type: "detection_rule", resource_id: "brute_force" })]);
    renderPage();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(await screen.findByText("Ran AI investigation")).toBeInTheDocument();
    expect(screen.getByText("Entries (2)")).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
  });

  it("links incident entries to the incident page", async () => {
    vi.mocked(getAuditLogs).mockResolvedValue([entry({})]);
    renderPage();
    expect(await screen.findByRole("link", { name: "INC-1001" })).toHaveAttribute("href", "/incidents/INC-1001");
  });

  it("says so when there is nothing to show", async () => {
    vi.mocked(getAuditLogs).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText("No audit entries in this view.")).toBeInTheDocument();
  });

  it("clicking a row reveals old and new values", async () => {
    vi.mocked(getAuditLogs).mockResolvedValue([entry({ old_value: { enabled: true }, new_value: { enabled: false } })]);
    renderPage();
    expect(screen.queryByText("Old value")).not.toBeInTheDocument();
    await userEvent.click(await screen.findByText("Ran AI investigation"));
    expect(screen.getByText("Old value")).toBeInTheDocument();
    expect(screen.getByText(/"enabled": false/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("Ran AI investigation"));
    expect(screen.queryByText("Old value")).not.toBeInTheDocument();
  });

  it("filtering by resource type re-queries the API", async () => {
    vi.mocked(getAuditLogs).mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(getAuditLogs).toHaveBeenCalledWith({ limit: 200, resource_type: undefined }));
    await userEvent.click(screen.getByRole("button", { name: "simulator" }));
    await waitFor(() => expect(getAuditLogs).toHaveBeenLastCalledWith({ limit: 200, resource_type: "simulator" }));
  });
});
