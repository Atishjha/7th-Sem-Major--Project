import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/services/api", () => ({ getHealth: vi.fn(), getMlStatus: vi.fn(), getSimulatorStatus: vi.fn(), getAiStatus: vi.fn() }));
import * as api from "@/services/api";
import SystemHealth from "@/pages/SystemHealth";

const healthy = { status: "ok", service: "AI Cyber Defense Command Center", environment: "development", time: "2026-10-01T10:00:00Z" };

const mockAi = { mode: "mock", provider: "mock", model: null, key_configured: false, label: "mock", note: "Offline analyst." } as const;

function mockUp() {
  vi.mocked(api.getAiStatus).mockResolvedValue(mockAi);
  vi.mocked(api.getHealth).mockResolvedValue(healthy);
  vi.mocked(api.getMlStatus).mockResolvedValue({ has_model: false, latest_run: null });
  vi.mocked(api.getSimulatorStatus).mockResolvedValue({ running: false, scenario: null, events_emitted: 0, total_events: null, started_at: null });
}

describe("SystemHealth page", () => {
  it("shows a healthy backend, an untrained model and an idle simulator", async () => {
    mockUp();
    render(<SystemHealth />);
    expect(await screen.findByText("healthy")).toBeInTheDocument();
    expect(screen.getByText("AI Cyber Defense Command Center")).toBeInTheDocument();
    expect(screen.getByText("not trained")).toBeInTheDocument();
    expect(screen.getByText("idle")).toBeInTheDocument();
  });

  it("reports a trained model honestly, including that unlabeled accuracy is not applicable", async () => {
    mockUp();
    vi.mocked(api.getMlStatus).mockResolvedValue({
      has_model: true,
      latest_run: { model_version: "v20261001", num_samples: 42, accuracy_status: "not_applicable" } as never,
    });
    render(<SystemHealth />);
    expect(await screen.findByText("trained")).toBeInTheDocument();
    expect(screen.getByText("v20261001")).toBeInTheDocument();
    expect(screen.getByText("not applicable (no labels)")).toBeInTheDocument();
  });

  it("shows the offline analyst by default", async () => {
    mockUp();
    render(<SystemHealth />);
    expect(await screen.findByText("offline mock")).toBeInTheDocument();
    expect(screen.getByText("not set")).toBeInTheDocument();
  });

  it("shows a live model, its name, and that a key is set (never the key)", async () => {
    mockUp();
    vi.mocked(api.getAiStatus).mockResolvedValue({
      mode: "live", provider: "groq", model: "llama-3.3-70b-versatile", key_configured: true,
      label: "llm:groq:llama-3.3-70b-versatile", note: "A failed call falls back to the offline analyst and the report says so.",
    });
    render(<SystemHealth />);
    expect(await screen.findByText("live model")).toBeInTheDocument();
    expect(screen.getByText("llama-3.3-70b-versatile")).toBeInTheDocument();
    expect(screen.getByText("set")).toBeInTheDocument();
    expect(screen.getByText(/falls back to the offline analyst/)).toBeInTheDocument();
  });

  it("explains a half-configured AI setup instead of pretending it is live", async () => {
    mockUp();
    vi.mocked(api.getAiStatus).mockResolvedValue({
      mode: "mock", provider: "groq", model: null, key_configured: false, label: "mock",
      note: "AI_PROVIDER is groq but AI_API_KEY is empty, so the offline analyst answers.",
    });
    render(<SystemHealth />);
    expect(await screen.findByText(/AI_API_KEY is empty/)).toBeInTheDocument();
    expect(screen.getByText("offline mock")).toBeInTheDocument();
  });

  it("shows the running scenario", async () => {
    mockUp();
    vi.mocked(api.getSimulatorStatus).mockResolvedValue({ running: true, scenario: "multi_stage", events_emitted: 4, total_events: 10, started_at: "x" });
    render(<SystemHealth />);
    expect(await screen.findByText("running")).toBeInTheDocument();
    expect(screen.getByText("multi_stage")).toBeInTheDocument();
  });

  it("flags an unreachable backend instead of showing stale data", async () => {
    vi.mocked(api.getHealth).mockRejectedValue(new Error("Failed to fetch"));
    vi.mocked(api.getMlStatus).mockRejectedValue(new Error("Failed to fetch"));
    vi.mocked(api.getSimulatorStatus).mockRejectedValue(new Error("Failed to fetch"));
    vi.mocked(api.getAiStatus).mockRejectedValue(new Error("Failed to fetch"));
    render(<SystemHealth />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unreachable: Failed to fetch");
    expect(screen.getByText("down")).toBeInTheDocument();
  });

  it("'Refresh now' re-checks, and recovery clears the error", async () => {
    vi.mocked(api.getHealth).mockRejectedValueOnce(new Error("boom"));
    vi.mocked(api.getMlStatus).mockRejectedValueOnce(new Error("boom"));
    vi.mocked(api.getSimulatorStatus).mockRejectedValueOnce(new Error("boom"));
    vi.mocked(api.getAiStatus).mockRejectedValueOnce(new Error("boom"));
    render(<SystemHealth />);
    await screen.findByRole("alert");
    mockUp();
    await userEvent.click(screen.getByRole("button", { name: "Refresh now" }));
    expect(await screen.findByText("healthy")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  describe("auto-refresh", () => {
    beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
    afterEach(() => vi.useRealTimers());

    it("polls every 10 seconds and stops when the page is left", async () => {
      mockUp();
      const { unmount } = render(<SystemHealth />);
      await screen.findByText("healthy");
      expect(api.getHealth).toHaveBeenCalledTimes(1);
      await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
      expect(api.getHealth).toHaveBeenCalledTimes(2);
      unmount();
      await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
      expect(api.getHealth).toHaveBeenCalledTimes(2);
    });
  });
});
