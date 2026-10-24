import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/hooks/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, getAllResponseActions: vi.fn(), approveResponseAction: vi.fn(), rejectResponseAction: vi.fn() };
});
import { useAuth } from "@/hooks/useAuth";
import * as api from "@/services/api";
import ResponseCenter from "@/pages/ResponseCenter";
import type { ResponseAction } from "@/types/response";

const action = (o: Partial<ResponseAction>): ResponseAction => ({
  id: 1, response_id: "RESP-000001", incident_id: 1, action_type: "isolate_endpoint", action_label: "Isolate Endpoint",
  target: "WIN-SRV-WEB01", recommended_reason: "Suspicious PowerShell.", status: "recommended",
  result_message: null, decided_by_username: null, decided_at: null, created_at: "2026-10-01T00:00:00Z", ...o,
});

function renderAs(role: string) {
  vi.mocked(useAuth).mockReturnValue({ user: { id: "1", username: role, role, is_active: true } } as never);
  return render(<MemoryRouter><ResponseCenter /></MemoryRouter>);
}

describe("ResponseCenter", () => {
  it("lists actions and counts the pending ones", async () => {
    vi.mocked(api.getAllResponseActions).mockResolvedValue([
      action({}), action({ id: 2, response_id: "RESP-000002", status: "rejected", result_message: "Rejected by analyst; no action taken." }),
    ]);
    renderAs("SOC_ANALYST");
    expect(await screen.findByText("RESP-000001")).toBeInTheDocument();
    expect(screen.getByText(/1 action\(s\) pending review/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Approve" })).toHaveLength(1);       // only the pending one
  });

  it("a viewer can see the queue but gets no decision buttons, and is told why", async () => {
    vi.mocked(api.getAllResponseActions).mockResolvedValue([action({})]);
    renderAs("VIEWER");
    await screen.findByText("RESP-000001");
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(screen.getByText(/can view this queue but not approve or reject/)).toBeInTheDocument();
  });

  it("admins and analysts are not shown the read-only notice", async () => {
    vi.mocked(api.getAllResponseActions).mockResolvedValue([action({})]);
    renderAs("ADMIN");
    await screen.findByText("RESP-000001");
    expect(screen.queryByText(/can view this queue but not/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("the status filter re-queries with the backend's status value", async () => {
    vi.mocked(api.getAllResponseActions).mockResolvedValue([]);
    renderAs("ADMIN");
    await waitFor(() => expect(api.getAllResponseActions).toHaveBeenCalledWith(undefined));
    await userEvent.click(screen.getByRole("button", { name: "Pending review" }));
    await waitFor(() => expect(api.getAllResponseActions).toHaveBeenLastCalledWith("recommended"));
  });

  it("states that nothing touches a real system", async () => {
    vi.mocked(api.getAllResponseActions).mockResolvedValue([]);
    renderAs("ADMIN");
    expect(await screen.findByText(/ever touches a real system/)).toBeInTheDocument();
  });
});
