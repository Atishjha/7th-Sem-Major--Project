import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, getToken: vi.fn(), setToken: vi.fn(), clearToken: vi.fn(), getMe: vi.fn(), login: vi.fn() };
});

import * as api from "@/services/api";
import { AuthProvider, useAuth } from "@/hooks/useAuth";

const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>;
const me = { id: "1", username: "analyst", role: "SOC_ANALYST", is_active: true };

beforeEach(() => vi.resetAllMocks());

describe("AuthProvider", () => {
  it("with no stored token it finishes loading logged-out and never calls the server", async () => {
    vi.mocked(api.getToken).mockReturnValue(null);
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(api.getMe).not.toHaveBeenCalled();
  });

  it("restores the session from a stored token", async () => {
    vi.mocked(api.getToken).mockReturnValue("tok");
    vi.mocked(api.getMe).mockResolvedValue(me as never);
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toEqual(me);
  });

  it("drops an invalid stored token", async () => {
    vi.mocked(api.getToken).mockReturnValue("stale");
    vi.mocked(api.getMe).mockRejectedValue(new api.ApiError(401, "nope"));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(api.clearToken).toHaveBeenCalled();
  });

  it("login stores the token and loads the profile", async () => {
    vi.mocked(api.getToken).mockReturnValue(null);
    vi.mocked(api.login).mockResolvedValue({ access_token: "newtok", token_type: "bearer", role: "SOC_ANALYST" } as never);
    vi.mocked(api.getMe).mockResolvedValue(me as never);
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(() => result.current.login("analyst", "analyst123"));
    expect(api.setToken).toHaveBeenCalledWith("newtok");
    expect(result.current.user).toEqual(me);
    expect(result.current.error).toBeNull();
  });

  it("failed login exposes the server's message, stays logged out, and rethrows", async () => {
    vi.mocked(api.getToken).mockReturnValue(null);
    vi.mocked(api.login).mockRejectedValue(new api.ApiError(401, "Incorrect username or password"));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await expect(result.current.login("x", "y")).rejects.toBeInstanceOf(api.ApiError);
    });
    expect(result.current.error).toBe("Incorrect username or password");
    expect(result.current.user).toBeNull();
    expect(api.setToken).not.toHaveBeenCalled();
  });

  it("a network failure shows a generic message", async () => {
    vi.mocked(api.getToken).mockReturnValue(null);
    vi.mocked(api.login).mockRejectedValue(new TypeError("Failed to fetch"));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.login("x", "y").catch(() => {});
    });
    expect(result.current.error).toBe("Unable to reach the server");
  });

  it("logout clears the token and the user", async () => {
    vi.mocked(api.getToken).mockReturnValue("tok");
    vi.mocked(api.getMe).mockResolvedValue(me as never);
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.user).not.toBeNull());
    act(() => result.current.logout());
    expect(api.clearToken).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
  });

  it("useAuth outside a provider is a clear error", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used within an AuthProvider");
    spy.mockRestore();
  });
});
