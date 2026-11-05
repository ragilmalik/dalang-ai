"use client";

import { modelLabel, type Job, type TraceEntry } from "@/lib/api";
import Icon from "@/components/ui/Icon";
import Bi from "@/components/ui/Bi";

const STAGE_LABEL: Record<string, string> = {
  listen: "Mendengar · Listening",
  lakon: "Menulis lakon · Writing",
  casting: "Wayang · Casting",
  scenes: "Adegan · Scenes",
  animate: "Gerak · Animate",
  narrate: "Suara · Narrate",
  cut: "Potongan akhir · Final cut",
};

function secs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

/** "Di balik kelir · Behind the screen": every Meta model call and agent decision behind this film. */
export default function AgentTrace({ job }: { job: Job }) {
  const trace: TraceEntry[] = job.trace || [];
  const summary = job.trace_summary;
  if (!trace.length || !summary) return null;
  const decisions = trace.filter((e) => e.kind === "decision");
  return (
    <details className="group card !p-0 text-sm" data-testid="agent-trace">
      <summary className="flex cursor-pointer list-none items-start gap-3 p-5 sm:p-6 [&::-webkit-details-marker]:hidden">
        <Icon name="eye" className="mt-1 h-6 w-6 shrink-0 text-gold" />
        <span className="flex-1">
          <span className="t-h3 block text-gold"><Bi stack id="Di balik kelir" en="Behind the screen" /></span>
          <span className="mt-1 block text-muted">
            {summary.calls} panggilan model Meta · Meta model calls
            {summary.decisions ? `, ${summary.decisions} keputusan agen · agent decisions` : ""}
          </span>
        </span>
        <Icon name="chevron" className="mt-1 h-5 w-5 shrink-0 text-gold transition-transform duration-kenong group-open:rotate-180" />
      </summary>
      <div className="space-y-3 px-5 pb-5 sm:px-6 sm:pb-6">
      {job.offline && (
        <p className="text-xs text-muted">
          Mode uji: panggilan dijawab oleh API Meta palsu bawaan · Test mode: answered by the built-in fake Meta API
          (same request and parsing code, placeholder art).
        </p>
      )}
      <div className="overflow-x-auto rounded-md border border-gold/10" tabIndex={0} role="region" aria-label="Meta model calls per model, table">
        <table className="tabular w-full text-left text-xs">
          <caption className="sr-only">Meta model calls per model</caption>
          <thead>
            <tr className="bg-fg/5 text-muted">
              <th scope="col" className="px-2 py-1.5">Model</th>
              <th scope="col" className="px-2 py-1.5">Panggilan · Calls</th>
              <th scope="col" className="px-2 py-1.5">Waktu · Time</th>
              <th scope="col" className="px-2 py-1.5">Biaya · Cost</th>
            </tr>
          </thead>
          <tbody>
            {summary.models.map((r) => (
              <tr key={r.model} className="border-t border-gold/10">
                <td className="py-1 pr-2 font-mono">{modelLabel(r.model)}</td>
                <td className="px-2 py-1.5">
                  {r.calls}
                  {r.retries ? ` (+${r.retries} retry)` : ""}
                  {r.failed ? ` · ${r.failed} failed` : ""}
                </td>
                <td className="px-2 py-1.5">{secs(r.ms)}</td>
                <td className="px-2 py-1.5">${r.usd.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {decisions.length > 0 && (
        <div>
          <h4 className="font-serif text-base font-semibold text-gold">Keputusan agen · Agent decisions</h4>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-xs">
            {decisions.map((d, i) => (
              <li key={i}>
                <span className="text-muted">[{d.agent}]</span> {d.text}
              </li>
            ))}
          </ul>
        </div>
      )}
      <details>
        <summary className="cursor-pointer text-xs font-semibold text-muted hover:text-fg">Semua langkah · Every step ({trace.length})</summary>
        <ol className="mt-1 space-y-0.5 pl-4 font-mono text-xs leading-snug">
          {trace.map((e, i) =>
            e.kind === "call" ? (
              <li key={i} className={e.ok ? "" : "text-err"}>
                {e.stage ? `${STAGE_LABEL[e.stage] || e.stage} · ` : ""}
                {e.model} {e.endpoint} · {e.purpose} · {secs(e.ms)}
                {e.attempts > 1 ? ` · ${e.attempts} tries` : ""}
                {e.ok ? "" : ` · ${e.error || "failed"}`}
              </li>
            ) : (
              <li key={i} className="text-gold/90">
                ↳ {e.agent}: {e.text}
              </li>
            ),
          )}
        </ol>
      </details>
      <p className="text-xs text-muted">
        JSON: <a className="link font-normal" href={`/api/jobs/${job.id}/trace`}>/api/jobs/{job.id}/trace</a>
      </p>
      </div>
    </details>
  );
}
