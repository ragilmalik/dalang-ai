"use client";

import { useEffect, useState } from "react";
import { deviceId, type Job, type VoteState } from "@/lib/api";
import Icon from "@/components/ui/Icon";
import Bi from "@/components/ui/Bi";

/** Each tap on the shared classroom screen is its own ballot (children without a phone vote at the board). */
function screenVoter(): string {
  return `${deviceId()}-screen-${Math.random().toString(36).slice(2, 8)}`;
}

/** Live tally bars, shared by the classroom screen and the phone voting page. */
export function Tally({ v, big = false }: { v: VoteState; big?: boolean }) {
  return (
    <div className="space-y-3" aria-live="polite" data-testid="vote-tally">
      {v.options.map((o, i) => {
        const n = v.tally[i] ?? 0;
        const pct = v.total ? Math.round((n * 100) / v.total) : 0;
        return (
          <div key={o}>
            <div className={`mb-1 flex justify-between gap-2 font-semibold ${big ? "text-lg" : "text-sm"}`}>
              <span>
                {i === 0 ? "🅰" : "🅱"} {o}
                {v.winner === i && " 🏆"}
              </span>
              <span className="tabular shrink-0">
                {n} ({pct}%)
              </span>
            </div>
            <div className={`${big ? "h-4" : "h-3"} overflow-hidden rounded-full bg-fg/10`}>
              <div
                className={`h-full rounded-full transition-[width] duration-gong ease-sabet ${i === 0 ? "bg-prada" : "bg-kembang"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
      <p className="tabular text-center text-sm text-muted">
        {v.total} suara · {v.total === 1 ? "vote" : "votes"}
      </p>
    </div>
  );
}

/**
 * Classroom mode for the gara-gara pause: the question on the big screen, a QR so every child votes from a phone,
 * live bars, and the teacher closes the vote to continue with the winning branch. Hidden when the API has no vote.
 */
export default function ClassroomVote({ job, onClosed }: { job: Job; onClosed: () => void }) {
  const [v, setV] = useState<VoteState | null>(null);
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(`/api/jobs/${job.id}/vote`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d: VoteState | null) => alive && setV(d))
        .catch(() => {});
    load();
    const t = on ? setInterval(load, 1500) : null;
    return () => {
      alive = false;
      if (t) clearInterval(t);
    };
  }, [job.id, on]);

  if (!v || v.status === "off") return null;

  async function cast(option: number) {
    setErr("");
    const r = await fetch(`/api/jobs/${job.id}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option, voter: screenVoter() }),
    }).catch(() => null);
    if (r?.ok) setV(await r.json());
    else setErr("Suara tidak terkirim · The vote did not go through.");
  }

  async function close() {
    setBusy(true);
    setErr("");
    const r = await fetch(`/api/jobs/${job.id}/vote/close`, { method: "POST" }).catch(() => null);
    if (r?.ok) onClosed();
    else {
      setErr(((await r?.json().catch(() => ({})))?.detail as string) || "Belum bisa ditutup · Could not close the vote.");
      setBusy(false);
    }
  }

  const path = `/vote/${job.id}`;
  return (
    <section className="card space-y-4" aria-labelledby="class-h" data-testid="classroom-vote">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="class-h" className="t-h2 flex items-start gap-2">
          <Icon name="teacher" className="h-7 w-7 text-gold" /> <Bi stack id="Mode kelas" en="Classroom vote" />
        </h2>
        <button type="button" className="btn" aria-pressed={on} onClick={() => setOn(!on)}>
          {on ? "Sembunyikan · Hide" : "Buka voting · Open the vote"}
        </button>
      </div>
      {!on && (
        <p className="text-muted">
          Biar seisi kelas memilih lewat HP masing-masing · Let the whole class choose from their phones.
        </p>
      )}
      {on && (
        <>
          <p className="kelir rounded-lg p-4 text-center font-display text-2xl font-medium leading-snug sm:text-3xl">{v.question}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {v.options.map((o, i) => (
              <button
                key={o}
                type="button"
                className={`min-h-24 rounded-xl px-4 py-6 text-xl font-bold text-on-prada transition-[transform,filter] duration-ketuk ease-sabet hover:brightness-110 active:translate-y-1 ${
                  i === 0 ? "bg-prada shadow-[0_4px_0_0_#a8741f]" : "bg-kembang shadow-[0_4px_0_0_#8a5ea3]"
                }`}
                onClick={() => cast(i)}
              >
                {i === 0 ? "🅰" : "🅱"} {o}
              </button>
            ))}
          </div>
          <div className="grid items-center gap-6 rounded-lg border border-gold/15 bg-bg-2/60 p-4 sm:grid-cols-[auto_1fr]">
            <figure className="mx-auto text-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/api/qr.png?path=${encodeURIComponent(path)}`}
                alt="QR code: scan to vote on your phone"
                width={180}
                height={180}
                className="rounded-lg bg-white p-2"
              />
              <figcaption className="mt-2 text-sm font-semibold">
                Pindai untuk memilih · Scan to vote
                <span className="block font-mono text-xs font-normal text-muted">{path}</span>
              </figcaption>
            </figure>
            <Tally v={v} big />
          </div>
          <button type="button" className="btn-gold btn-lg w-full" disabled={busy || v.total === 0} aria-busy={busy || undefined} onClick={close}>
            {busy ? <span className="spinner" aria-hidden="true" /> : <Icon name="gamelan" className="h-6 w-6" />} Tutup voting, lanjutkan cerita · Close the vote and continue
          </button>
          <p className="text-center text-sm text-muted">Seri? Pilihan 🅰 menang · A tie goes to 🅰.</p>
        </>
      )}
      {err && (
        <p role="alert" className="text-center text-sm text-err">
          {err}
        </p>
      )}
    </section>
  );
}
