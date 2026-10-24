import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/hooks/useAuth", () => ({ useAuth: vi.fn() }));
import { useAuth } from "@/hooks/useAuth";
import Login from "@/pages/Login";

function setup(auth: Partial<ReturnType<typeof useAuth>>) {
  const value = { user: null, loading: false, error: null, login: vi.fn().mockResolvedValue(undefined), logout: vi.fn(), ...auth };
  vi.mocked(useAuth).mockReturnValue(value as never);
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>HOME</div>} />
      </Routes>
    </MemoryRouter>
  );
  return value;
}

describe("Login page", () => {
  it("submits what the user typed", async () => {
    const auth = setup({});
    await userEvent.type(screen.getByLabelText(/username/i), "analyst");
    await userEvent.type(screen.getByLabelText(/password/i), "analyst123");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(auth.login).toHaveBeenCalledWith("analyst", "analyst123");
    await waitFor(() => expect(screen.getByText("HOME")).toBeInTheDocument());
  });

  it("shows the auth error and stays on the page when login fails", async () => {
    const auth = setup({ error: "Incorrect username or password" });
    (auth.login as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("x"));
    await userEvent.type(screen.getByLabelText(/username/i), "admin");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(screen.getByText("Incorrect username or password")).toBeInTheDocument();
    expect(screen.queryByText("HOME")).not.toBeInTheDocument();
  });

  it("does not render the password in clear text", () => {
    setup({});
    expect(screen.getByLabelText(/password/i)).toHaveAttribute("type", "password");
  });

  it("sends an already signed-in user straight to the app", () => {
    setup({ user: { id: "1", username: "a", role: "ADMIN", is_active: true } as never });
    expect(screen.getByText("HOME")).toBeInTheDocument();
  });
});
