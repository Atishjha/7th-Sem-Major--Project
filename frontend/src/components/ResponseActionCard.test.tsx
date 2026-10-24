import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, approveResponseAction: vi.fn(), rejectResponseAction: vi.fn() };
});
import * as api from "@/services/api";
import { ResponseActionCard } from "@/components/ResponseActionCard";
import type { ResponseAction } from "@/types/response";

const base: ResponseAction = {
  id: 1, response_id: "RESP-000001", incident_id: 1, action_type: "disable_account", action_label: "Disable Account",
  target: "demo_user", recommended_reason: "Account shows signs of compromise.", status: "recommended",
  result_message: null, decided_by_username: null, decided_at: null, created_at: "2026-10-01T00:00:00Z",
};

describe("ResponseActionCard", () => {
  it("shows Approve/Reject only for a pending action the user may decide", () => {
    const { rerender } = render(<ResponseActionCard action={base} canDecide onDecided={() => {}} />);
    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();

    rerender(<ResponseActionCard action={base} canDecide={false} onDecided={() => {}} />);   // viewer
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();

    rerender(<ResponseActionCard action={{ ...base, status: "simulated_success" }} canDecide onDecided={() => {}} />);
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();      // already decided
  });

  it("approving calls the API for this action and reports the updated action", async () => {
    const updated = { ...base, status: "simulated_success" as const };
    vi.mocked(api.approveResponseAction).mockResolvedValue(updated);
    const onDecided = vi.fn();
    render(<ResponseActionCard action={base} canDecide onDecided={onDecided} />);
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(api.approveResponseAction).toHaveBeenCalledWith("RESP-000001");
    await waitFor(() => expect(onDecided).toHaveBeenCalledWith(updated));
  });

  it("rejecting calls the reject endpoint, not approve", async () => {
    vi.mocked(api.rejectResponseAction).mockResolvedValue({ ...base, status: "rejected" });
    render(<ResponseActionCard action={base} canDecide onDecided={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(api.rejectResponseAction).toHaveBeenCalledWith("RESP-000001");
    expect(api.approveResponseAction).not.toHaveBeenCalled();
  });

  it("shows the server's error (e.g. already decided) and does not report success", async () => {
    vi.mocked(api.approveResponseAction).mockRejectedValue(new api.ApiError(409, "Action is already 'rejected'"));
    const onDecided = vi.fn();
    render(<ResponseActionCard action={base} canDecide onDecided={onDecided} />);
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByText("Action is already 'rejected'")).toBeInTheDocument();
    expect(onDecided).not.toHaveBeenCalled();
  });

  it("displays the simulated-result message and who decided", () => {
    render(<ResponseActionCard canDecide onDecided={() => {}} action={{
      ...base, status: "simulated_success", decided_by_username: "analyst",
      result_message: "Demo account 'demo_user' would be disabled. No real account was modified." }} />);
    expect(screen.getByText(/No real account was modified/)).toBeInTheDocument();
    expect(screen.getByText(/decided by analyst/)).toBeInTheDocument();
  });
});
