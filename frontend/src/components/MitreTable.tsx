import type { MitreTechnique } from "@/types/ai";

/** The plain Tactic/Technique/ID/Confidence table, reused by the AI
 * investigation report and the Incident Page's own MITRE tab —
 * both render exactly the spec's per-technique field list. */
export function MitreTable({ techniques }: { techniques: MitreTechnique[] }) {
  if (techniques.length === 0) {
    return <p className="text-xs text-muted font-mono">No techniques mapped for this incident's rules.</p>;
  }
  return (
    <table className="w-full text-xs font-mono">
      <thead>
        <tr className="text-left text-muted border-b border-line">
          <th className="py-1 pr-4">Tactic</th>
          <th className="py-1 pr-4">Technique</th>
          <th className="py-1 pr-4">ID</th>
          <th className="py-1">Confidence</th>
        </tr>
      </thead>
      <tbody>
        {techniques.map((m) => (
          <tr key={m.technique_id} className="border-b border-line/50">
            <td className="py-1 pr-4 text-slate-300">{m.tactic}</td>
            <td className="py-1 pr-4 text-slate-200">{m.technique_name}</td>
            <td className="py-1 pr-4 text-signal">{m.technique_id}</td>
            <td className="py-1 text-muted">{m.confidence}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
