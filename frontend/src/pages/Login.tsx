import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

export default function Login() {
  const { user, login, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    const redirectTo = (location.state as { from?: string })?.from ?? "/";
    return <Navigate to={redirectTo} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch {
      // error is already surfaced via useAuth().error
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-lg font-semibold text-slate-100">
            AI Cyber Defense Command Center
          </h1>
          <p className="text-sm text-muted">Sign in to access the SOC console</p>
        </div>

        <Panel>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="username" className="text-sm text-slate-300">
                Username
              </label>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
                className="w-full rounded-sm border border-line bg-ink-950 px-3 py-2 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-signal"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm text-slate-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-sm border border-line bg-ink-950 px-3 py-2 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-signal"
              />
            </div>

            {error && (
              <p className="text-sm text-severity-critical" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </Panel>

        <Panel className="bg-ink-800/30">
          <p className="text-xs font-medium text-severity-medium mb-2">
            Demo credentials — not for production
          </p>
          <dl className="grid grid-cols-3 gap-2 font-mono text-xs text-muted">
            <div>
              <dt className="text-slate-400">admin</dt>
              <dd>admin123</dd>
            </div>
            <div>
              <dt className="text-slate-400">analyst</dt>
              <dd>analyst123</dd>
            </div>
            <div>
              <dt className="text-slate-400">viewer</dt>
              <dd>viewer123</dd>
            </div>
          </dl>
        </Panel>
      </div>
    </div>
  );
}
