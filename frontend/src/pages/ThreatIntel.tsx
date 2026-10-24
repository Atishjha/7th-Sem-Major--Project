import { Panel } from "@/components/ui/panel";

export default function ThreatIntel() {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">Threat Intelligence</h1>
      <Panel title="Not part of this project">
        <div className="px-4 py-3 space-y-2 text-sm text-muted">
          <p>
            This console does not query external threat-intelligence feeds, and nothing here pretends to.
            All telemetry is synthetic and uses non-routable addresses (RFC 5737 / RFC 1918) and
            <span className="font-mono"> .invalid </span> domains, so there is nothing real to look up.
          </p>
          <p>
            What it does provide: the indicators extracted from each incident (IPs, hosts, accounts) appear in
            that incident&apos;s AI investigation report, ready to be checked against a real feed.
          </p>
        </div>
      </Panel>
    </div>
  );
}
