import { Panel } from "@/components/ui/panel";

interface ComingSoonProps {
  title: string;
  phaseNote: string;
}

export default function ComingSoon({ title, phaseNote }: ComingSoonProps) {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-slate-100">{title}</h1>
      <Panel className="text-center py-12">
        <p className="text-sm text-muted">
          This module isn't built yet — {phaseNote}.
        </p>
      </Panel>
    </div>
  );
}
