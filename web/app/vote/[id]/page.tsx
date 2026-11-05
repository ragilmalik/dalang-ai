"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Tally } from "@/components/ClassroomVote";
import { deviceId, type VoteState } from "@/lib/api";
import Gunungan from "@/components/ui/Gunungan";
import Icon from "@/components/ui/Icon";
import { buttonClass } from "@/components/ui/Button";

/** The phone side of classroom mode: two huge buttons, one vote per phone (tapping again changes it). */
export default function VotePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [v, setV] = useState<VoteState | null>(null);
  const [missing, setMissing] = useState(false);
  const [mine, setMine] = useState<number | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch(`/api/jobs/${encodeURIComponent(id)}/vote`)
        .then((r) => {
          if (r.status === 404) setMissing(true);
          return r.ok ? r.json() : null;
        })
        .then((d: VoteState | null) => alive && d && setV(d))
        .catch(() => {});
    load();
    const t = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [id]);

  async function cast(option: number) {
    setErr("");
    const r = await fetch(`/api/jobs/${encodeURIComponent(id)}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option, voter: deviceId() }),
    }).catch(() => null);
    if (r?.ok) {
      setV(await r.json());
      setMine(option);
    } else setErr(r?.status === 409 ? "Voting sudah ditutup · The vote is closed." : "Coba lagi · Please try again.");
  }

  if (missing)
    return (
      <div className="card mx-auto mt-12 max-w-md space-y-4 text-center" role="alert">
        <Gunungan className="mx-auto h-16 w-12 text-gold" />
        <p className="t-h3">Tidak ada voting untuk film ini · There is no vote for this film.</p>
        <Link href="/" className={buttonClass("primary")}>
          Dalang AI
        </Link>
      </div>
    );
  if (!v)
    return (
      <div className="grid min-h-[50vh] place-items-center" role="status">
        <div className="space-y-3 text-center">
          <Gunungan className="kayon-sway mx-auto h-16 w-12 text-gold" />
          <p className="text-muted">Memuat · Loading…</p>
        </div>
      </div>
    );
  return (
    <div className="mx-auto max-w-md space-y-6 pt-8 text-center">
      <span className="blencong mx-auto block" aria-hidden="true" />
      <h1 className="t-h1 flex items-center justify-center gap-3 text-gold">
        <Icon name="wind" className="h-9 w-9" /> Gara-gara!
      </h1>
      {v.status === "off" ? (
        <p className="card">Belum ada pertanyaan · No question yet. Tunggu sebentar · Wait a moment…</p>
      ) : (
        <>
          <p className="kelir rounded-xl p-5 font-display text-2xl font-medium leading-snug">{v.question}</p>
          {v.status === "open" ? (
            <div className="grid gap-4">
              {v.options.map((o, i) => (
                <button
                  key={o}
                  type="button"
                  aria-pressed={mine === i}
                  onClick={() => cast(i)}
                  className={`min-h-28 rounded-xl px-4 py-6 text-2xl font-bold text-on-prada transition-[transform,box-shadow] duration-ketuk ease-sabet active:translate-y-1 ${
                    i === 0 ? "bg-prada shadow-[0_6px_0_0_#a8741f]" : "bg-kembang shadow-[0_6px_0_0_#8a5ea3]"
                  } ${mine === i ? "ring-4 ring-fg ring-offset-4 ring-offset-bg" : ""}`}
                >
                  {i === 0 ? "🅰" : "🅱"} {o}
                  {mine === i && <span className="mt-1 block text-base">✓ pilihanku · my vote</span>}
                </button>
              ))}
            </div>
          ) : (
            <p className="card text-lg">
              Voting ditutup · The vote is closed.{" "}
              {v.winner !== null && (
                <span className="mt-2 block font-display text-2xl text-gold">
                  🏆 {v.options[v.winner]}
                </span>
              )}
            </p>
          )}
          {mine !== null && (
            <p className="text-sm text-ok" role="status">
              Suaramu masuk! Ketuk lagi untuk mengganti · Your vote is in! Tap again to change it.
            </p>
          )}
          <div className="card text-left">
            <Tally v={v} />
          </div>
        </>
      )}
      {err && (
        <p role="alert" className="text-err">
          {err}
        </p>
      )}
      <Link href={`/film/${id}`} className={buttonClass("secondary")}>
        <Icon name="monitor" /> Lihat layar besar · Big screen view
      </Link>
    </div>
  );
}
