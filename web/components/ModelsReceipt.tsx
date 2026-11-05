import { modelLabel, type Job } from "@/lib/api";
import Icon from "@/components/ui/Icon";
import Bi from "@/components/ui/Bi";

const RULE_LABEL: Record<string, string> = {
  "gentle-conflict": "Konflik lembut · Gentle conflict",
  "no-politics": "Tanpa politik · No politics",
  "no-gore": "Tanpa darah · No gore",
  "respect-figures": "Hormati tokoh · Respect figures",
  "kid-friendly-pictures": "Gambar ramah anak · Child-friendly pictures",
  canon: "Sesuai pakem · True to the tale",
  "no-invented-ritual": "Tanpa ritual karangan · No invented ritual",
  "gunungan-respect": "Gunungan dihormati · Gunungan respected",
};

function n(x: number): string {
  return x.toLocaleString("en-US");
}

/** Penjaga Budaya report + character consistency + "Meta models used" receipt for one film. */
export default function ModelsReceipt({ job }: { job: Job }) {
  const rec = job.receipt;
  const cr = job.cultural_review;
  const con = job.consistency;
  if (!rec && !cr && !con) return null;
  return (
    <section className="card space-y-6 text-sm" data-testid="models-receipt">
      {cr && (
        <div data-testid="cultural-review">
          <h3 className="t-h3 flex items-start gap-2 text-gold"><Icon name="shield" className="mt-0.5 h-6 w-6" /><Bi stack id="Penjaga Budaya" en="Cultural guardian" /></h3>
          <p className="mt-2 text-muted">
            {cr.model || "Pemeriksa kata"} memeriksa setiap adegan dengan {cr.rules.length} aturan budaya sebelum digambar:{" "}
            {Math.round(cr.pass_rate_first * 100)}% lolos sejak awal, {cr.fixes} diperbaiki,{" "}
            {Math.round(cr.pass_rate_after * 100)}% lolos akhirnya.
          </p>
          <p lang="en" className="mt-1 text-muted opacity-80">
            {cr.model || "The word scan"} checked every scene against {cr.rules.length} cultural rules before drawing:{" "}
            {Math.round(cr.pass_rate_first * 100)}% passed first time, {cr.fixes} fixed, {Math.round(cr.pass_rate_after * 100)}%
            passed after fixes.
          </p>
          <ul className="mt-3 flex flex-wrap gap-1.5 text-xs">
            {cr.scenes.map((s) => (
              <li key={s.n} className={`rounded-md px-2.5 py-1 font-semibold ${s.passed_first ? "bg-ok/10 text-ok" : "bg-err/15 text-fg"}`}>
                Adegan {s.n}: {s.passed_first ? "✓" : `diperbaiki · fixed (${s.rules.map((r) => RULE_LABEL[r] || r).join(", ")})`}
              </li>
            ))}
          </ul>
          <p className="t-tiny mt-2 text-muted">{cr.rules_status}</p>
        </div>
      )}
      {con && con.puppets.length > 0 && (
        <div data-testid="consistency">
          <h3 className="t-h3 flex items-start gap-2 text-gold"><Icon name="scissors" className="mt-0.5 h-6 w-6" /><Bi stack id={<>Konsistensi tokoh <span className="tabular">{con.score}/100</span></>} en={`Character consistency: ${con.score}/100`} /></h3>
          <p className="mt-2 text-muted">
            Satu potongan SAM 3.1 per wayang, dipakai ulang di {con.appearances} kemunculan.
          </p>
          <p lang="en" className="mt-1 text-muted opacity-80">
            One SAM 3.1 cut-out per puppet, reused pixel for pixel in {con.appearances} scene appearances.
          </p>
          <ul className="mt-2 space-y-1 text-xs">
            {con.puppets.map((p) => (
              <li key={p.id}>
                {p.name}: {p.score}/100 · {p.source === "background" ? "background key (no SAM mask)" : p.source === "kotak" ? "Kotak Wayang (SAM)" : "SAM 3.1 mask"}
                {" · "}
                {p.same_pixels ? "same pixels in every scene" : "pixels changed"}
                {p.checker_redraws ? ` · ${p.checker_redraws} redraw` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
      {rec && rec.models.length > 0 && (
        <div data-testid="receipt">
          <h3 className="t-h3 flex items-start gap-2 text-gold"><Icon name="receipt" className="mt-0.5 h-6 w-6" /><Bi stack id="Model Meta yang dipakai" en="Meta models used" /></h3>
          {/* phones get one small card per model; the full table from sm up */}
          <ul className="mt-3 space-y-2 sm:hidden">
            {rec.models.map((r) => (
              <li key={r.model} className="rounded-md border border-gold/10 bg-fg/5 px-3 py-2">
                <p className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span className="font-mono font-semibold">{modelLabel(r.model)}</span>
                  <span className="tabular text-xs text-muted">
                    {r.calls} calls{r.images ? ` (${r.images} img)` : ""} · ${r.usd.toFixed(3)}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-muted">{r.role}</p>
              </li>
            ))}
            <li className="tabular flex flex-wrap justify-between gap-x-3 px-3 pt-1 text-xs font-semibold">
              <span>
                Total: {rec.calls} calls · {rec.decisions} agent decisions
              </span>
              <span>${rec.usd.toFixed(3)}</span>
            </li>
          </ul>
          <div className="mt-3 hidden overflow-x-auto rounded-md border border-gold/10 sm:block">
            <table className="tabular w-full text-left text-xs">
              <caption className="sr-only">Meta models used to make this film</caption>
              <thead>
                <tr className="bg-fg/5 text-muted">
                  <th scope="col" className="px-2 py-1.5">Model</th>
                  <th scope="col" className="px-2 py-1.5">Tugas · Job</th>
                  <th scope="col" className="px-2 py-1.5">Calls</th>
                  <th scope="col" className="px-2 py-1.5">Tokens in / out</th>
                  <th scope="col" className="px-2 py-1.5">Cost (est.)</th>
                </tr>
              </thead>
              <tbody>
                {rec.models.map((r) => (
                  <tr key={r.model} className="border-t border-gold/10">
                    <td className="whitespace-nowrap px-2 py-1.5 font-mono">{modelLabel(r.model)}</td>
                    <td className="px-2 py-1.5">{r.role}</td>
                    <td className="px-2 py-1.5">
                      {r.calls}
                      {r.images ? ` (${r.images} img)` : ""}
                    </td>
                    <td className="px-2 py-1.5">{r.tokens_in || r.tokens_out ? `${n(r.tokens_in)} / ${n(r.tokens_out)}` : "-"}</td>
                    <td className="px-2 py-1.5">${r.usd.toFixed(3)}</td>
                  </tr>
                ))}
                <tr className="border-t border-gold/30 font-semibold">
                  <td className="px-2 py-1.5">Total</td>
                  <td className="px-2 py-1.5">{rec.decisions} agent decisions</td>
                  <td className="px-2 py-1.5">{rec.calls}</td>
                  <td className="px-2 py-1.5">
                    {n(rec.tokens_in)} / {n(rec.tokens_out)}
                  </td>
                  <td className="px-2 py-1.5">${rec.usd.toFixed(3)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="t-tiny mt-2 text-muted">
            {rec.note} Prices:{" "}
            <a className="link font-normal" href={rec.pricing} target="_blank" rel="noreferrer">
              dev.meta.ai pricing
            </a>{" "}
            · JSON: <a className="link font-normal" href={`/api/jobs/${job.id}/receipt`}>/api/jobs/{job.id}/receipt</a>
          </p>
        </div>
      )}
    </section>
  );
}
