import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/hooks/useAuth", () => ({ useAuth: vi.fn() }));
import { useAuth } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/ProtectedRoute";

function renderAt(state: { user: unknown; loading: boolean }) {
  vi.mocked(useAuth).mockReturnValue(state as never);
  return render(
    <MemoryRouter initialEntries={["/secret"]}>
      <Routes>
        <Route path="/login" element={<div>LOGIN PAGE</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/secret" element={<div>SECRET CONTENT</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("redirects anonymous visitors to /login and never renders the page", () => {
    renderAt({ user: null, loading: false });
    expect(screen.getByText("LOGIN PAGE")).toBeInTheDocument();
    expect(screen.queryByText("SECRET CONTENT")).not.toBeInTheDocument();
  });

  it("shows a loading state (not a redirect) while the session is being checked", () => {
    renderAt({ user: null, loading: true });
    expect(screen.getByText(/Checking session/)).toBeInTheDocument();
    expect(screen.queryByText("LOGIN PAGE")).not.toBeInTheDocument();
    expect(screen.queryByText("SECRET CONTENT")).not.toBeInTheDocument();
  });

  it("renders the page for a signed-in user", () => {
    renderAt({ user: { username: "a", role: "VIEWER" }, loading: false });
    expect(screen.getByText("SECRET CONTENT")).toBeInTheDocument();
  });
});
