import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Radio,
  ShieldAlert,
  Brain,
  Bell,
  FolderKanban,
  Gauge,
  Bot,
  Crosshair,
  Globe,
  Zap,
  ScrollText,
  Database,
  PlayCircle,
  HeartPulse,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/events", label: "Event Monitor", icon: Radio },
  { to: "/detection", label: "Detection Engine", icon: ShieldAlert },
  { to: "/ml", label: "ML Anomaly Detection", icon: Brain },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/incidents", label: "Incidents", icon: FolderKanban },
  { to: "/risk", label: "Risk Engine", icon: Gauge },
  { to: "/ai-analyst", label: "AI SOC Analyst", icon: Bot },
  { to: "/mitre", label: "MITRE ATT&CK", icon: Crosshair },
  { to: "/threat-intel", label: "Threat Intelligence", icon: Globe },
  { to: "/response", label: "Response Center", icon: Zap },
  { to: "/audit", label: "Audit Logs", icon: ScrollText },
  { to: "/dataset", label: "Dataset & ML", icon: Database },
  { to: "/demo", label: "Demo Mode", icon: PlayCircle },
  { to: "/system-health", label: "System Health", icon: HeartPulse },
];

export default function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex bg-ink-950 text-slate-100">
      <aside className="w-60 shrink-0 border-r border-line bg-ink-900 flex flex-col">
        <div className="h-14 flex items-center px-4 border-b border-line">
          <span className="h-2 w-2 rounded-full bg-signal mr-2" />
          <span className="text-sm font-semibold tracking-tight">SOC Console</span>
        </div>

        <nav className="flex-1 overflow-y-auto py-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-4 py-2 text-sm border-l-2 transition-colors",
                  isActive
                    ? "border-signal bg-ink-800/60 text-slate-100"
                    : "border-transparent text-muted hover:text-slate-200 hover:bg-ink-800/30"
                )
              }
            >
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 flex items-center justify-between px-6 border-b border-line bg-ink-900/60">
          <span className="text-xs uppercase tracking-wide text-muted font-mono">
            Educational demo — synthetic data only
          </span>
          <div className="flex items-center gap-4">
            <div className="text-sm text-right leading-tight">
              <div className="text-slate-200">{user?.username}</div>
              <div className="text-xs text-muted">{user?.role}</div>
            </div>
            <button
              onClick={logout}
              className="text-muted hover:text-severity-critical transition-colors"
              title="Log out"
            >
              <LogOut size={18} strokeWidth={1.75} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
